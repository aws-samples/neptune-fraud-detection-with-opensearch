#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights served.
SPDX-License-Identifier: MIT-0
 
Permission is hereby granted, free of charge, to any person taining a copy of this
software and associated documentation files (the oftware"), to deal in the Software
without restriction, including without limitation the rights  use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies  the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY ND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF RCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL E AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, ETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN NNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import logging
from retrying import retry
from elasticsearch import Elasticsearch, RequestsHttpConnection, TransportError
from elasticsearch.helpers import bulk, BulkIndexError
from requests_aws4auth import AWS4Auth
import abc
import six
from cachetools import cached, TTLCache

from handler import AbstractHandler, HandlerResponse
from commons import *

from aggregator.es_aggregator import ElasticSearchAggregator
from neptune_to_es import es_helper
from config_provider import config_provider
from credential_provider import credential_provider

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)


# Elastic Search Literals
ES_AGGREGATE_QUERY_SIZE = 50
SERVICE = 'es'

# Elastic Search Configuration
ES_ENDPOINT = es_helper.get_url_components(config_provider
                                                    .get_handler_additional_param('ElasticSearchEndpoint'))
IGNORE_MISSING_DOCUMENT_ERROR = config_provider.get_handler_additional_param('IgnoreMissingDocument') != 'false'

# Painless Script to add field to respective ES document.
# Painless Script is used to update specific field within a document.
# Reference Doc - https://www.elastic.co/guide/en/elasticsearch/reference/master/modules-scripting-painless.html
# Queries generated using painless script are idempotent and thus can handle duplicate
# records. Painless script can also update multiple fields for same document in one go.
# Below script append different values for same property Key in a list.
ADD_FIELD_SCRIPT = '''void add(def object, def key, def value){
                         if (object[key] != null) {
                            if(!object[key].contains(value)) {
                                object[key].add(value)
                            } 
                         }else {
                            object[key] = [value]
                         }
                      }
                      for (predicate in params.predicates){
                          if (predicate["key"]=="entity_type"){
                              add(ctx._source, predicate["key"], predicate["value"])
                          }
                          else {
                              if (ctx._source["predicates"] == null){
                                 ctx._source["predicates"] = new HashMap()
                              }  
                              add(ctx._source.predicates, predicate["key"], predicate["value"])
                          }
                      }'''


# Painless Script to delete Property from respective ES document.
# This script take care of duplicate requests using Delete only if present
# check. Script also removes property key from Vertex document if no more
# values present after delete.
DROP_FIELD_SCRIPT = '''void remove(def object, def key, def value){
                         if (object[key] != null) {
                             object[key].removeIf(x -> x.equals(value));
                             if (object[key].length == 0){
                                object.remove(key)
                             }
                         }
                       }  
                       for (predicate in params.predicates){
                           if (predicate["key"]=="entity_type"){
                               remove(ctx._source, predicate["key"], predicate["value"])
                           }
                           else if(ctx._source["predicates"] != null){
                               remove(ctx._source.predicates, predicate["key"], predicate["value"])
                           }   
                       }
                       if (ctx._source["predicates"] != null && ctx._source.predicates.size() == 0){
                           ctx._source.remove("predicates")    
                       }
                       if(ctx._source.size() == 2){
                           ctx.op = "delete" 
                       }else{ 
                           ctx.op = "index"
                       }'''

# ES Client connection Cache with TTL
_es_connection_cache = TTLCache(maxsize=1, ttl=900)   # TTL is in Seconds

# Record Aggregator
aggregator = ElasticSearchAggregator()


def __initial_setup__(es_client):

    """
    Do initial setup for Elastic Search by creating relevant indices
    """

    # Checking Elastic Search version
    es_helper.validate_es_version(es_client)

    logger.info("Trying to Create Index for Elastic Search")
    es_helper.create_index(es_client, es_helper.INDEX)


def __base_action__(document_id, query_type):

    """
    Generates action object with generic fields for Elastic search bulk API.
    This action object needs to be updated for doing specific Bulk operations.

    :param document_id: Unique Id for ES document
    :param query_type: Type of operation on ES
    :return: Json object to be used to generate actions for Elastic search Bulk API
    """

    return {
        "_type": "_doc",
        "_index": es_helper.INDEX,
        "_id": document_id,
        "_op_type": query_type
    }


def __update_action__(document_id, script_source, params_json, upsert_json=None):

    """
    Generates action object to perform update operation in Elastic Search using Bulk API.
    Update action object is generated using base action object.
    Update action can have upsert field for use cases like update or insert. Upsert field can
    be assigned a document object using :upsert_json parameter. When no document with :document_id
    is present to update , document object from upsert field will be inserted as new Elastic Search
    document.

    :param document_id: Unique Id for ES document
    :param script_source: Painless script source
    :param params_json: Value referenced from Painless Script. Ex : For updating Properties it can be property values.
                        For Vertex / Edge  insert it can be Labels.
    :param upsert_json: Document json to be inserted in Elastic Search when no valid Document found to update.
    :return: Json object to be used as an Action for Elastic search Update Operation
    """

    action = __base_action__(document_id, "update")
    action["script"] = {
        "source": script_source,
        "lang": "painless",
        "params": {
            "predicates": params_json
        }
    }

    if upsert_json:
        action["upsert"] = upsert_json

    return action


def __delete_action__(document_id):

    """
    Generate action object to perform delete operation in Elastic Search using Bulk API.
    Delete action object is generated using base action object.

    :param document_id: Unique Id for Elastic Search document
    :return: Json object to be used as an action for Elastic search delete operation
    """

    return __base_action__(document_id, "delete")


def __retryable_error__(exception):

    """
    Checks if exception is retry-able
    :param exception: Exception thrown
    :return: True or False
    """

    if exception is not None and isinstance(exception, TransportError):
        logger.info("Retrying...")
        return True
    return False


def __check_missing_document_error__(error):

    """
    Check if Elastic Search error is due to missing document.
    :param error: Elastic Search error object
    :return: boolean
    """

    try:
        if 'update' in error and error['update']['status'] == 404 \
                and 'type' in error['update']['error'] and \
                error['update']['error']['type'] == 'document_missing_exception':
            return True
    except Exception:
        # Process should not fail due to unknown error parsing exception.
        return False

    return False


@six.add_metaclass(abc.ABCMeta)
class ElasticSearchBaseHandler(AbstractHandler):

    """
    Abstract class to replicate Stream Records to a target Elastic Search Service.
    Stream Records are converted to appropriate Elastic Search documents and updated in
    Elastic Search Service using Bulk API.
    """

    def __init__(self):
        __initial_setup__(self.__get_es_client())

    @cached(_es_connection_cache)
    def __get_es_client(self):

        """
           Returns Elastic Search Client. If no client exists this method will
           create new client else will return a client from Cache
           :return: Elastic Search Client
        """

        try:
            logger.info("Creating an Elastic Search client with endpoint - {}:{}".format(ES_ENDPOINT["host"],
                                                                                         ES_ENDPOINT["port"]))

            # Authentication
            aws_auth = AWS4Auth(credential_provider.get_access_key(), credential_provider.get_secret_key(),
                                config_provider.region, SERVICE, session_token=credential_provider.get_security_token())

            # Elastic Search service connection
            return Elasticsearch(
                hosts=[{'host': ES_ENDPOINT["host"], 'port': int(ES_ENDPOINT["port"])}],
                http_auth=aws_auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
        except Exception as e:
            logger.error("Error Creating elastic search client with endpoint - {}:{}".format(ES_ENDPOINT["host"],
                                                                                             ES_ENDPOINT["port"]))
            raise e


    @abc.abstractmethod
    def build_query(self, operation_type, record_data_lists):

        """
        Abstract Method to build  Elastic Search query from stream records. Different query statement are built
        based on Stream Record Operation values.

        :param operation_type: Operation Type corresponding to Stream record Ex: ADD_vl, REMOVE_e
        :param record_data_lists: Aggregated List of stream records data object
        :return: Elastic Search Query statement
        """

        pass

    @abc.abstractmethod
    def add_query_builder_map(self):
        """
        Abstract method to build query builder map
        """
        pass

    @abc.abstractmethod
    def generate_es_field_key(self, record_data):

        """
        Abstract Method to generate Elastic Search document field Key from Stream Record data.

        :param record_data: Stream Record data
        :return: Elastic Search Document field key
        """

        pass

    @abc.abstractmethod
    def generate_es_field_value(self, record_data):

        """
        Abstract Method to generate Elastic Search document field value from Stream Record data.

        :param record_data: Stream Record data
        :return: Elastic Search Document field value
        """

        pass

    @abc.abstractmethod
    def filter_records(self, records, es_client):

        """
        Abstract Method to filter records to be stored in Elastic Search.

        :param records: Stream Records list
        :param es_client: Client for ES connection
        :return: Filtered Record List
        """

        pass

    def get_add_field_script(self):

        """
        Returns Elastic Search Painless script to add/update fields in Elastic Search Document.
        This method can be overriden by sub-classes to source another script for Elastic search
        document update.
        :return: Elastic Search Painless script to add/update Fields in Document
        """

        return ADD_FIELD_SCRIPT

    def get_drop_field_script(self):

        """
        Returns Elastic Search Painless script to delete fields from Elastic Search Document.
        This method can be overriden by sub-classes to source another script for Elastic search
        document update.
        :return: Elastic Search Painless script to delete Fields from Document
        """

        return DROP_FIELD_SCRIPT

    def __generate_Action__(self, record_data_list, operation):

        """
        Generates an Elastic search bulk update action using list of Stream records.

        :param record_data_list: List of stream record data referenced to generate single Elastic Search action
        :param operation: Stream record operation i.e. ADD or REMOVE
        :return: Elastic Search Bulk API Action to perform
        """

        script_source = self.get_add_field_script() if operation == "ADD" else self.get_drop_field_script()
        params_json = []
        document_id = es_helper.generate_es_document_id(record_data_list[0])
        for record_data in record_data_list:
            # Adding Stream Record Property key & property value as Elastic search query parameter
            params_json.append(
                {
                    "key": self.generate_es_field_key(record_data),
                    "value": self.generate_es_field_value(record_data)
                }
            )
        return __update_action__(document_id, script_source,
                                 params_json, None)

    @abc.abstractmethod
    def get_upsert_json(self, record_data_list):

        """
        Abstract Method to generate Upsert Document value. Upsert Document value is used by Elastic search update query
        to insert a new document if no document is present for update.

        :param record_data_list: List of stream record data referenced to generate Elastic Search query upsert document
        :return: Upsert document Json
        """
        pass

    def __update_query__(self, record_data_lists, operation, require_upsert=False):
        """
        Generates Elastic Search action to update a document.

        :param record_data_lists: List of bundle of Stream records data which can be combined together to  create
         single Elastic search action.
        :param operation: Stream record operation i.e. ADD or REMOVE
        :param require_upsert: Boolean to check if Upsert Document is required for Elastic Search Update Action.
        :return: Elastic Search action to update a document
        """

        for record_data_list in record_data_lists:
            action = self.__generate_Action__(record_data_list, operation)
            if require_upsert:
                action["upsert"] = self.get_upsert_json(record_data_list)
            yield action

    def __delete_query__(self, record_data_lists):

        """
        Generates Elastic Search action to delete a document.

        :param record_data_lists: List of bundle of Stream records data which can be combined together to  create
         single Elastic search action.
        :return: Elastic Search action to delete a document
        """

        for record_data_list in record_data_lists:
            for record_data in record_data_list:
                yield __delete_action__(es_helper.generate_es_document_id(record_data))

    def __generate_aggregated_es_actions__(self, records):

        """
        Generate list of Elastic search Actions for Bulk API call. This method take stream records
        & aggregate them before generating Actions from them.

        :param records: Stream Records
        :return: List of Elastic search Actions for Bulk API call
        """

        action_list = []

        # Aggregate Stream records in appropriate bundles
        aggregate_map = aggregator.aggregate_records(records)
        for aggregate_entry in aggregate_map.values():
            for records_set in aggregate_entry[RECORDS_SET_STR]:
                action_list.extend(list(self.build_query(records_set[OPERATION_STR],
                                                         split_list(records_set[RECORDS_STR],
                                                                    ES_AGGREGATE_QUERY_SIZE))))
        return action_list

    @retry(retry_on_exception=__retryable_error__, wait_exponential_multiplier=1000, stop_max_attempt_number=5)
    def __execute_query(self, actions, raise_error=True):

        """
        Executes query on Elastic Search. Will do retry using exponential backoff
        for retryable exceptions.
        :param actions: Elastic Search Bulk API actions
        """

        try:
            logger.debug("Executing bulk actions on Elastic Search - {}".format(str(actions)))
            success, errors = bulk(self.__get_es_client(), actions, max_retries=3, chunk_size=2000,
                                   stats_only=False, raise_on_error=raise_error, raise_on_exception=True)

            if not raise_error:
                # When Ignoring Missing Document exceptions, check all bulk api errors are due to missing Document only.
                # If not appropriate Exception is thrown.
                for error in errors:
                    if not __check_missing_document_error__(error):
                        raise BulkIndexError("%i document(s) failed to index." % len(errors), errors)
                logger.info("Completed Elastic search Bulk query after ignoring Missing document exception. "
                            "Success: {}, Ignored Missing Document: {}".format(success, len(errors)))
            else:
                logger.info("Completed Elastic search Bulk query. "
                            "Success: {}, Failed: {}, Errors: {}".format(success, len(errors), errors))
        except BulkIndexError as err:
            # Checking if Bulk update can be retried in case of Document Missing Exception.
            if IGNORE_MISSING_DOCUMENT_ERROR and len(err.errors) > 0 and \
                    __check_missing_document_error__(err.errors[0]) and raise_error:

                logger.info("Retrying after ignoring Document Missing Exception - {}.".format(err.errors[0]))
                self.__execute_query(actions, False)
            else:
                logger.error("Error Occurred: {}, Message: {}, Errors: {}".format("BulkIndexError", err, err.errors))
                raise
        except TransportError as err:
            logger.error("Exception Occurred: {}, Message: {}".format("TransportError", err))
            raise

    def handle_records(self, stream_log):

        """
        Method to Handle Stream records. This method is called from Lambda Function to process records.
        This method perform below steps sequentially :

        1) Filter out Stream Records not to be stored in Elastic Search
        2) Build Elastic Search Actions from filtered Stream records
        2) Execute Query on Elastic Search using Bulk API
        3) Yield HandlerResponse

        :param stream_log: Neptune Stream Change log

        """

        logger.info("Starting ES data replication !!!")

        # Filtering out Records not to be stored in Elastic Search
        records = self.filter_records(stream_log[RECORDS_STR], self.__get_es_client())
        actions = self.__generate_aggregated_es_actions__(records)
        logger.info("About to copy data to ES !!!")
        try:
            logger.info("Doing Bulk update for Elastic Search using Stream records with" +
                        " last event id (commitNum, opNum) - {}, {}"
                        .format(stream_log[LAST_EVENT_ID][COMMIT_NUM_STR], stream_log[LAST_EVENT_ID][OP_NUM_STR]))
            self.__execute_query(actions)

            yield HandlerResponse(stream_log[LAST_EVENT_ID][OP_NUM_STR], stream_log[LAST_EVENT_ID][COMMIT_NUM_STR],
                                  stream_log[TOTAL_RECORDS])
        except Exception as e:
            logger.error("Error Occurred - {}  while doing bulk update to Elastic Search endpoint {}:{} "
                         .format(str(e), ES_ENDPOINT["host"], ES_ENDPOINT["port"]))
            raise e
