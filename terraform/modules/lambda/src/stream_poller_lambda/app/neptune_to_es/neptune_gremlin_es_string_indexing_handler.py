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



from neptune_to_es.es_helper import *
from neptune_to_es.neptune_gremlin_es_handler import ElasticSearchGremlinHandler
from neptune_to_es.datatype_validators import *

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)

# Elastic Search Configuration
IGNORE_MISSING_DOCUMENT_ERROR = config_provider.get_handler_additional_param('IgnoreMissingDocument') != 'false'
DROP_EDGE = config_provider.get_handler_additional_param('ReplicationScope') == 'nodes'
ENABLE_NON_STRING_INDEXING = config_provider.get_handler_additional_param('EnableNonStringIndexing') == 'true'
datatypes = set(datatype.value for datatype in DataType)

class ElasticSearchStringOnlyGremlinHandler(ElasticSearchGremlinHandler):

    """
    Replicates Stream records to a target Elastic Search Service.
    Stream Records are converted to appropriate Elastic Search documents and updated in
    Elastic Search using Bulk API. To minimize update requests sent to Elastic Search, this class sends
    a single update request for a bundle of Stream records.

    Note: This class will replicate only String data and non-string data would be dropped.

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

    def __convert_property_value__(self, value):
        """
        Converts property value from Stream record to appropriate Elastic Search format when only String indexing is enabled.

        :param value: Value object from Stream Record
        :return: Value in appropriate format
        """

        value_type = value[PROPERTY_VALUE_TYPE_STR]
        if value_type == 'Date':
            return get_date_time_from_millis(value[PROPERTY_VALUE_STR])
        return value[PROPERTY_VALUE_STR]

    def generate_es_field_value(self, record_data):

        """
        Generates Elastic Search document field nested value from Stream Record data.

        :param record_data: Stream Record data
        :return: Elastic Search Document field value
        """
        # For Vertex/Edge Label directly return value instead of dictionary
        if record_data[PROPERTY_KEY_STR] == LABEL_STR:
            return record_data[PROPERTY_VALUE_STR][PROPERTY_VALUE_STR]

        return {
            "value": self.__convert_property_value__(record_data[PROPERTY_VALUE_STR])
        }

    def filter_records(self, records, client):

        """
        Filters record to be stored in Elastic Search.
        For Gremlin Language, Stream Records are filtered out based on below logic:
        0) drop a record representing edge or edge property if user has selected to drop edge updates.
        1) drop a record representing property, if its value is not of type string

        :param client: Elastic Search client
        :param records: Stream Records list
        :return: Filtered Record List
        """

        for record in records:

            record_data = record[DATA_STR]
            if DROP_EDGE and record_data[TYPE_STR] in ["e", "ep"]:
                # Case  0) drop a record representing edge or edge property if user has selected to drop edge updates.
                logger.debug("Dropping Record : Edge updates not needed to process - {}".format(str(record_data)))
            elif record_data[TYPE_STR] in ["vp", "ep"] and not (record_data[PROPERTY_VALUE_STR][PROPERTY_VALUE_TYPE_STR].lower() == "string"):
                # Case 1) drop a record representing property, if its value is not of type string
                logger.debug("Dropping Record : Property value is not string for record {}".format(str(record_data)))
            else:
                yield record
