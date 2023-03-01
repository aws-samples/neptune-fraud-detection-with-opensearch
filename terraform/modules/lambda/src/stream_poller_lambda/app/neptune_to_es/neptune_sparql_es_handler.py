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


from rdflib.term import BNode, Literal
from neptune_to_es.datatype_validators import *
from neptune_to_es.es_helper import *
from elasticsearch.exceptions import RequestError
from commons import *
from neptune_to_es.neptune_to_es_handler import ElasticSearchBaseHandler
from config_provider import config_provider
import math

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)


def get_datatype_token(object_type):

    """
    Parse clean type string from datatype URI in format namespace#datatype.
    If no datatype can be retrieved then default to string datatype
    Ex. "<http://www.w3.org/2001/XMLSchema#integer>” -> "integer"

    :param object_type: Full datatype URI string from stream record object
    :return: Datatype string value
    """

    type = re.search(r"(?<=http://www.w3.org/2001/XMLSchema#)[^<]+", object_type)

    return type[0] if type else DataType.STRING.value


class ElasticSearchSparqlHandler(ElasticSearchBaseHandler):
    """
        Replicates Stream Records to a target Elastic Search Service.
        Stream Records are converted to appropriate Elastic Search documents and updated in
        Elastic Search Service using Bulk API. To minimize update requests sent to Elastic Search, this class sends
        a single update request for a bundle of Stream records.

        This Class uses single index (amazon_neptune index) to store Sparql data. Elastic Search index stores
        Triples/ Quad data as object based document with all possible pairs of predicate & object for same
        Subject in a single document. Document id for Elastic Search document is created using md5 of (Subject) value
        from Sparql Statement.

        Object value corresponding to a predicate is Stored as a nested object in Elastic Search.
        Sample:
        {
            "value" : "propValue1",         // Value of Property
            "datatype" : ":propDatatypeURI",   // DataType URI corresponding to Neptune DB. Not present for String Literals
            "graph" : ":namedGraphURI", // Named Graph URI value. Present only if Predicate-Object pair belongs to a Named Graph.
            "language" : "en"  // Present only for rdf:langString
        }

        Below is the sample representations of Sparql Document.

        {
            "_index": "amazon_neptune",
            "_type": "_doc",
            "_id": "723c31fc529b23952d1f21b165a8f437",
            "_version": 2,
            "_score": 1,
            "_source": {
                "entity_id" : ":subjectURI",
                "entity_type" : [ ":type1", ":type2"],  // Object value corresponding to :rdfType Predicate of Subject
                "document_type" : "rdf-resource",
                "predicates" : {
                    ":fooPredicate" : [
                        {
                          "value" : "value1"
                        },
                        {
                          "value" : "value2",
                          "graph" : ":namedGraph1"      // Predicate-Object Pair belongs to a Named Graph(:namedGraph1)
                        }
                    ],
                    ":barProperty" : [
                        {
                          "value" : "value3",
                          "language" : "en"         //object is LangString Literal -> "value3"@en
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
        self.query_builder_map = {
            'ADD': lambda x: self.__update_query__(x, "ADD", True),
            'REMOVE': lambda x: self.__update_query__(x, "REMOVE")
        }

    def build_query(self, operation_type, record_data_lists):

        """
        Build Elastic Search query from stream records. Different query statements are built
        based on stream record operation type.

        Stream record operations:
        ADD : Statement Added
        REMOVE : Statement removed

        :param operation_type: Operation Type corresponding to Stream record Ex: ADD, REMOVE
        :param record_data_lists: Aggregated list of stream records data object
        :return: Elastic Search query statement
        """

        return self.query_builder_map[operation_type](record_data_lists)

    def generate_es_field_key(self, record_data):

        """
        Generates Elastic Search document field Key from Stream Record data.

        :param record_data: Stream Record data
        :return: Elastic Search Document field key
        """

        statement_elements = record_data[ELEMENTS_STR]

        # Resolving rdf:type in Sparql to "entity_type" for unifying Model for Gremlin & Sparql
        if statement_elements[PREDICATE].eq(RDF_TYPE):
            return ElasticSearchDocumentFields.ENTITY_TYPE.value
        else:
            return str(statement_elements[PREDICATE])

    def generate_es_field_value(self, record_data):

        """
        Generates Elastic Search document field Nested value from Stream Record data.

        :param record_data: Stream Record data
        :return: Elastic Search Document field value
        """

        statement_elements = record_data[ELEMENTS_STR]

        # For rdf:type Predicate directly return value instead of dictionary
        if statement_elements[PREDICATE].eq(RDF_TYPE):
            return str(statement_elements[OBJECT])

        es_type = record_data[ES_TYPE_STR] if ES_TYPE_STR in record_data else DataType.STRING.value
        obj_value = statement_elements[OBJECT].value if statement_elements[OBJECT].value \
            else str(statement_elements[OBJECT].toPython())

        # Converter here
        if statement_elements[OBJECT].datatype:

            value = {
                "value": convert_to_es_value(es_type, obj_value),
                "datatype": str(statement_elements[OBJECT].datatype)
            }
        else:
            value = {
                "value": str(obj_value)
            }

        # Appending Graph information in case of Named Graph
        if GRAPH in statement_elements:
            value[GRAPH] = str(statement_elements[GRAPH])

        # Appending Language information in case of rdf:langString Literal
        if statement_elements[OBJECT].language:
            if validate_language(statement_elements[OBJECT].language):
                value[LANGUAGE] = str(statement_elements[OBJECT].language)

        return value

    def filter_records(self, records, client):

        """
        Filters records to be stored in Elastic Search.
        For Sparql Language, Stream Records are filtered out if:
        1) Subject is a Blank Node
        2) Object is a Resource for predicates other than rdf:type
        3) Predicate name present in excluded_properties list
        4) Object type is present in excluded_types list
        5) Object if of type lang literal and lang fails regex check
        6) Object if of type Float/ Double literal and value is not finite i.e. NaN, INF, -INF
        7) Property value invalid for property type specified for record
        8) Object is any literal and its value cannot be converted to appropriate ES type.


        :param client: ElasticSearch client
        :param records: Stream records list
        :return: Filtered records list
        """

        excluded_types = get_excluded_datatypes("sparql")
        excluded_properties = get_excluded_properties()

        # Copy of Neptune ES index mappings for local use
        es_index_mapping_cache = client.indices.get_mapping(index='amazon_neptune')

        # Handling property names representing geoPoint data. Passed by users as config value.
        add_geo_location_mapping(client, es_index_mapping_cache)

        for record in records:
            record_data = record[DATA_STR]
            statement_elements = parse_sparql_statement(record_data)
            # Storing parsed SPARQL statement in-memory for further usage
            record_data[ELEMENTS_STR] = statement_elements
            if isinstance(statement_elements[SUBJECT], BNode):
                # case 1) Subject is a Blank Node
                logger.debug("Dropping Record : Rdf Resource is represented by Blank Node for record {}"
                             .format(str(record_data)))
            elif statement_elements[PREDICATE].neq(RDF_TYPE):
                # case 2) Object is a Resource for predicates other than rdf:type
                if not isinstance(statement_elements[OBJECT], Literal):
                    logger.debug("Dropping Record : Rdf Object value is not a literal for record {}"
                                 .format(str(record_data)))
                else:
                    obj_key = str(statement_elements[PREDICATE])
                    obj_value = statement_elements[OBJECT].value if statement_elements[OBJECT].value \
                        else str(statement_elements[OBJECT].toPython())
                    obj_datatype = str(statement_elements[OBJECT].datatype)
                    obj_datatype_token = get_datatype_token(obj_datatype).strip().lower()

                    if obj_key.strip() in excluded_properties:
                        # case 3) Predicate name present in excluded_properties list
                        logger.debug("Dropping Record : Property name found in list of indicated properties to exclude for record {}"
                                     .format(str(record_data)))
                        continue

                    if obj_datatype_token in excluded_types:
                        # case 4) Object type is present in excluded_types list
                        logger.debug(
                            "Dropping Record : Property type found in list of indicated datatypes to exclude for record {}"
                                .format(str(record_data)))
                        continue

                    if obj_datatype_token == DataType.STRING.value and statement_elements[OBJECT].language:
                        obj_lang = statement_elements[OBJECT].language
                        if not validate_language(obj_lang):
                            # case 5) Object if of type lang literal and lang fails regex check
                            logger.debug(
                                "Dropping Record : String literal has invalid language tag for record {}"
                                .format(str(record_data))
                            )
                            continue

                    if obj_datatype_token in {DataType.FLOAT.value, DataType.DOUBLE.value, DataType.DECIMAL.value}:
                        # Need to confirm is obj_value is float otherwise error is thrown
                        if is_valid_float_value(obj_value) and (math.isinf(float(obj_value)) or math.isnan(float(obj_value))):
                            # case 6) Object if of type Float/ Double / Decimal  literal and value is not finite
                            # i.e. NaN, INF, -INF
                            logger.debug(
                                "Dropping Record : Float literal does not have finite value for record {}"
                                    .format(str(record_data)))
                            continue

                    # Get current type mapping for key from local mapping store
                    field_mapping_type_in_es = get_current_mapping_for_predicate(obj_key, es_index_mapping_cache)

                    # If no mapping exists for property key, then create it
                    if not field_mapping_type_in_es:
                        # Strings always get dynamic mapped correctly by ES
                        try:
                            field_mapping_type_in_es = get_es_type_for_neptune_type(obj_datatype_token)
                            if validate(obj_value, field_mapping_type_in_es):
                                es_index_mapping_cache = add_mapping_to_es(client, es_index_mapping_cache, obj_key,
                                                                           obj_datatype_token)
                                record_data[ES_TYPE_STR] = field_mapping_type_in_es
                                yield record
                            else:
                                # case 7) Property value invalid for property type specified for record
                                logger.debug(
                                    "Dropping Record : Property value invalid for property type specified for record {}"
                                    .format(str(record_data))
                                )
                        except RequestError as e:
                            if e.error == "illegal_argument_exception":
                                # case 8) Object is any literal and its value cannot be converted to appropriate ES type.
                                logger.debug("Concurrency issue detected! - {}. Property mapping with conflicting "
                                             "type already exists in index. Refreshing mappings.".format(str(e)))
                                es_index_mapping_cache = client.indices.get_mapping(index='amazon_neptune')
                                logger.debug("Dropping Record : Property value does not match index "
                                             "type mapping for record {}".format(str(record_data)))
                            else:
                                raise e
                    else:
                        # If mapping does exist, validate property type and/or value against ES type mapping
                        if validate(obj_value, field_mapping_type_in_es):
                            record_data[ES_TYPE_STR] = field_mapping_type_in_es
                            yield record
                        else:
                            # case 8) Object is any literal and its value cannot be converted to appropriate ES type.
                            logger.debug(
                                "Dropping Record : Property type does not match indexed type mapping for record {}"
                                .format(str(record_data))
                            )
            else:
                yield record


    def get_upsert_json(self, record_data_list):

        """
        Generates Upsert Document value. Upsert Document value is used by Elastic search update query
        to insert a new document if no document is present for update.

        :param record_data_list: List of stream record data referenced to generate Elastic Search query upsert Document
        :return: Upsert Document Json
        """

        statement_elements = record_data_list[0][ELEMENTS_STR]

        # Adding Subject & Document Type to upsert document model
        upsert_doc = {
            ElasticSearchDocumentFields.ENTITY_ID.value: str(statement_elements[SUBJECT]),
            ElasticSearchDocumentFields.DOCUMENT_TYPE.value: DocumentType.RDF_RESOURCE.value
        }

        # Adding Predicated to the upsert Document
        for record_data in record_data_list:
            field_key = self.generate_es_field_key(record_data)
            field_value = self.generate_es_field_value(record_data)
            if field_key == ElasticSearchDocumentFields.ENTITY_TYPE.value:
                upsert_doc.setdefault(field_key, []).append(field_value)
            else:
                # Handling the case when same predicate have two different values. On first occurrence
                # of predicate, blank list is assigned as value. And Object value is appended to the blank List.
                # On second occurrence of predicate new object value is appended to the value List.
                upsert_doc.setdefault(ElasticSearchDocumentFields.PREDICATES.value, {})\
                    .setdefault(field_key, []).append(field_value)

        return upsert_doc
