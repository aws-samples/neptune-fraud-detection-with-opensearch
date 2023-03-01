#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights served.
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

from elasticsearch.exceptions import RequestError

from neptune_to_es.es_helper import *
from neptune_to_es.neptune_to_es_handler import ElasticSearchBaseHandler
from neptune_to_es.datatype_validators import *

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)

# Elastic Search Configuration
IGNORE_MISSING_DOCUMENT_ERROR = config_provider.get_handler_additional_param('IgnoreMissingDocument') != 'false'
DROP_EDGE = config_provider.get_handler_additional_param('ReplicationScope') == 'nodes'
datatypes = set(datatype.value for datatype in DataType)

class ElasticSearchGremlinHandler(ElasticSearchBaseHandler):

    """
    Replicates Stream records to a target Elastic Search Service.
    Stream Records are converted to appropriate Elastic Search documents and updated in
    Elastic Search using Bulk API. To minimize update requests sent to Elastic Search, this class sends
    a single update request for a bundle of Stream records.
    Ex: Adding 'N' properties for a Vertex in a single transaction in Neptune will result in 'N' change
    Log Events. Aggregator will combine all these N updates applicable for same Vertex and fire a
    single update request in Elastic Search using Painless Script.

    This Class uses single Elastic Search index (amazon_neptune) to store Gremlin data. Each document in Elastic
    Search represent either a Vertex or Edge and stores all the relevant information i.e. Properties, Labels
    corresponding to Vertex / Edge in the Same Document. Vertex / Edge documents in Elastic Search can be
    differentiated using 'document_type' field.

    Elastic Search document id is MD5 hash of PREFIX + vertex/edge ID. PREFIX (v:// for vertex, e:// for edge)
    is used to avoid Id collision between Edge & Vertex document.

    Property value for a Vertex is Stored as a nested object in Elastic Search.
    Sample:
    {
        "value" : "propValue1",         // Value of Property
        "datatype" : "propDatatype",    // DataType of Property corresponding to Neptune DB. Not present for string Literals
    }

    Below is the sample representations of Elastic Search Document corresponding to Gremlin.


    VERTEX -
    {
        "_index": "amazon_neptune",
        "_type": "_doc",
        "_id": "723c31fc529b23952d1f21b165a8f437",
        "_version": 2,
        "_score": 1,
        "_source": {
            "entity_id" : "151",
            "entity_type" : [ "label1", "label2"],
            "document_type" : "vertex",            // For Edge "document_type" : "edge"
            "predicates" : {
                "fooProperty" : [
                    {
                      "value" : "value1"
                    },
                    {
                      "value" : "value2"
                    }
                ],
                "barProperty" : [
                    {
                      "value" : "value3"
                    }
                ]
            }
        }
    }

    """

    def __init__(self):
        super().__init__()
        self.add_query_builder_map()

    def add_query_builder_map(self):
        # If IGNORE_MISSING_DOCUMENT is set to true than need to do upsert while adding property for vertex/ edge
        # in Elastic Search. Doing upsert will ensure we will not get document missing exception.
        self.query_builder_map = {
            'ADD_vl': lambda x: self.__update_query__(x, "ADD", True),
            'ADD_vp': lambda x: self.__update_query__(x, "ADD", IGNORE_MISSING_DOCUMENT_ERROR),
            'ADD_e': lambda x: self.__update_query__(x, "ADD", True),
            'ADD_ep': lambda x: self.__update_query__(x, "ADD", IGNORE_MISSING_DOCUMENT_ERROR),
            'REMOVE_vl': lambda x: self.__update_query__(x, "REMOVE"),
            'REMOVE_vp': lambda x: self.__update_query__(x, "REMOVE"),
            'REMOVE_e': lambda x: self.__update_query__(x, "REMOVE"),
            'REMOVE_ep': lambda x: self.__update_query__(x, "REMOVE")
        }

    def build_query(self, operation_type, record_data_lists):

        """
        Build Gremlin query from stream records. Different query statements are built
        based on Stream Record Operation values.

        Stream record operations:
        ADD_vl : Vertex Added
        ADD_vp : Vertex Property added
        ADD_e : Edge Added
        ADD_ep : Edge Property Added
        REMOVE_vl : Vertex Deleted
        REMOVE_vp : Vertex property Deleted
        REMOVE_e : Edge Deleted
        REMOVE_ep : Edge Property Deleted

        :param operation_type: Operation Type corresponding to Stream record Ex: ADD_vl, REMOVE_e
        :param record_data_lists: Aggregated List of stream records data object
        :return: Elastic Search Query statement
        """

        return self.query_builder_map[operation_type](record_data_lists)

    def generate_es_field_key(self, record_data):

        """
        Generates Elastic Search document field Key from Stream Record data.

        :param record_data: Stream Record data
        :return: Elastic Search Document field key
        """

        # Resolving label in Gremlin to "entity_type" for unifying Model for Gremlin & Sparql
        return record_data[PROPERTY_KEY_STR] if record_data[PROPERTY_KEY_STR] != LABEL_STR \
            else ElasticSearchDocumentFields.ENTITY_TYPE.value

    def generate_es_field_value(self, record_data):

        """
        Generates Elastic Search document field nested value from Stream Record data.

        :param record_data: Stream Record data
        :return: Elastic Search Document field value
        """

        predicate_value = record_data[PROPERTY_VALUE_STR][PROPERTY_VALUE_STR]
        es_type = record_data[ES_TYPE_STR] if ES_TYPE_STR in record_data else DataType.STRING.value

        # For Vertex/Edge Label directly return value instead of dictionary
        if record_data[PROPERTY_KEY_STR] == LABEL_STR:
            return record_data[PROPERTY_VALUE_STR][PROPERTY_VALUE_STR]

        if record_data[PROPERTY_VALUE_STR][PROPERTY_VALUE_TYPE_STR].lower() == DataType.STRING.value:
            return {
                "value": convert_to_es_value(es_type, predicate_value)
            }
        else:
            return {
                "value": convert_to_es_value(es_type, predicate_value),
                "datatype": record_data[PROPERTY_VALUE_STR][PROPERTY_VALUE_TYPE_STR]
            }

    def filter_records(self, records, client):

        """
        Filters record to be stored in Elastic Search.
        For Gremlin Language, Stream Records are filtered out based on below logic:
        0) drop a record representing edge or edge property if user has selected to drop edge updates.
        1) drop a record representing property, if it is present in excluded_properties
        2) drop a record representing property, if its value is of type present in excluded_types
        3) drop a record representing property, if its value cannot be converted to an existing ES mapping.
        4) drop a record representing property, if its data type is not a valid Gremlin type

        :param client: Elastic Search client
        :param records: Stream Records list
        :return: Filtered Record List
        """

        # Property types to be excluded
        excluded_types = get_excluded_datatypes("gremlin")
        # Properties to be excluded
        excluded_properties = get_excluded_properties()

        # Copy of Neptune ES index mappings. For each Stream API call we fetch mappings once.
        es_index_mapping_cache = client.indices.get_mapping(index='amazon_neptune')

        # Handling property names representing geoPoint data. Passed by users as config value.
        add_geo_location_mapping(client, es_index_mapping_cache)

        for record in records:

            record_data = record[DATA_STR]
            if DROP_EDGE and record_data[TYPE_STR] in ["e", "ep"]:
                # Case  0) drop a record representing edge or edge property if user has selected to drop edge updates.
                logger.debug("Dropping Record : Edge updates not needed to process - {}".format(str(record_data)))
            elif record_data[TYPE_STR] in ["vp", "ep"]:
                record_type = record_data[PROPERTY_VALUE_STR][PROPERTY_VALUE_TYPE_STR]
                record_value = record_data[PROPERTY_VALUE_STR][PROPERTY_VALUE_STR]
                record_key = record_data[PROPERTY_KEY_STR]

                if record_type.lower() not in datatypeMapping:
                    # Case 4) drop a record representing property, if its data type is not a valid Gremlin type
                    logger.debug("Dropping Record : Data type not a valid Gremlin type for record {}".format(str(record_data)))
                    continue

                # convert milliseconds to iso date format string. This conversion is done as we
                # don't want to validate long value to be valid for conversion to Date format.
                if record_type.lower() == DataType.DATE.value:
                    record_value = get_date_time_from_millis(record_value)

                if record_key.strip() in excluded_properties:
                    # Case 1) drop a record representing property, if it is present in excluded_properties
                    logger.debug("Dropping Record : Property name found in indicated properties "
                                 "to exclude for record {}".format(str(record_data)))
                    continue

                if record_type.strip().lower() in excluded_types:
                    # Case 2) drop a record representing property, if its value is of type present in excluded_types
                    logger.debug("Dropping Record : Property type found in indicated datatypes to exclude for record {}"
                                 .format(str(record_data)))
                    continue

                # Get current type mapping for key from local mapping store
                field_mapping_type_in_es = get_current_mapping_for_predicate(record_key, es_index_mapping_cache)

                # If no mapping exists for property key, then create it
                if not field_mapping_type_in_es:
                    try:
                        es_index_mapping_cache = add_mapping_to_es(client, es_index_mapping_cache, record_key,
                                                                   record_type)
                        record_data[ES_TYPE_STR] = get_es_type_for_neptune_type(record_type)
                        yield record
                    except RequestError as e:
                        if e.error == "illegal_argument_exception":
                            # case 3) drop a record representing property, if its value cannot be converted
                            logger.debug("Concurrency issue detected! - {}. Property mapping with conflicting "
                                         "type already exists in index. Refreshing mappings.".format(str(e)))
                            es_index_mapping_cache = client.indices.get_mapping(index='amazon_neptune')
                            logger.debug("Dropping Record : Property value does not match index "
                                         "type mapping for record {}".format(str(record_data)))
                        else:
                            raise e
                else:
                    # If mapping does exist, validate property type and/or value against ES type mapping
                    if validate(record_value, field_mapping_type_in_es):
                        record_data[ES_TYPE_STR] = field_mapping_type_in_es
                        yield record
                    else:
                        # case 3) drop a record representing property, if its value cannot be converted
                        # to an existing ES mapping.
                        logger.debug("Dropping Record : Property type does not match indexed type mapping - {} for record {}"
                                     .format(field_mapping_type_in_es, str(record_data)))
            else:
                yield record

    def get_upsert_json(self, record_data_list):

        """
        Generates Upsert Document value. Upsert Document value is used by Elastic search update query
        to insert a new document if no document is present for update.

        :param record_data_list: List of stream record data referenced to generate upsert Document
                                 for Elastic search query
        :return: Upsert Document Json
        """

        record_data = record_data_list[0]
        operation_type = record_data[TYPE_STR]
        document_type = DocumentType.VERTEX.value if operation_type in ["vl", "vp"] else DocumentType.EDGE.value
        entity_id = record_data[ID_STR]

        # Adding Subject & Document Type to upsert document model
        upsert_doc = {
            ElasticSearchDocumentFields.ENTITY_ID.value: entity_id,
            ElasticSearchDocumentFields.DOCUMENT_TYPE.value: document_type
        }

        # Adding Predicates to the upsert Document
        for record_data in record_data_list:
            field_key = self.generate_es_field_key(record_data)
            field_value = self.generate_es_field_value(record_data)
            if field_key == ElasticSearchDocumentFields.ENTITY_TYPE.value:
                upsert_doc.setdefault(field_key, []).append(field_value)
            else:
                # Handling the case when same predicate have two different values. On first occurrence
                # of predicate, blank list is assigned as value. And Object value is appended to the blank List.
                # On second occurrence of predicate new object value is appended to the value List.
                upsert_doc.setdefault(ElasticSearchDocumentFields.PREDICATES.value, {}) \
                    .setdefault(field_key, []).append(field_value)

        return upsert_doc
