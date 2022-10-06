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


"""
Helper File to help setup Elastic Search Cluster
"""

import logging
import hashlib
import datetime
from dateutil.parser import parse, ParserError
from datetime import datetime as dt

from packaging import version
from commons import *
from enum import Enum
from config_provider import config_provider, set_config_provider

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)

# Elastic Search Configuration
NO_OF_SHARDS = int(config_provider.get_handler_additional_param('NumberOfShards', 5))
NO_OF_REPLICA = int(config_provider.get_handler_additional_param('NumberOfReplica', 1))
GEO_LOCATION_FIELDS = config_provider.get_handler_additional_param('GeoLocationFields', '')
DATATYPES_TO_EXCLUDE = config_provider.get_handler_additional_param('DatatypesToExclude', '')
PROPERTIES_TO_EXCLUDE = config_provider.get_handler_additional_param('PropertiesToExclude', '')
OPEN_SEARCH_DISTRIBUTION = "opensearch"

# Elastic Search Model Literals
INDEX = "amazon_neptune"
VERTEX_ID_Prefix = "v://"
EDGE_ID_PREFIX = "e://"

# Lists of valid types for SPARQL and Gremlin
VALID_SPARQL_TYPES = {"string", "boolean", "float", "double", "datetime", "byte", "int", "long", "short",
                      "date", "decimal", "integer", "nonnegativeinteger", "nonpositiveinteger", "negativeinteger",
                      "unsignedbyte", "unsignedint", "unsignedlong", "unsignedshort", "time"}
VALID_GREMLIN_TYPES = {"string", "date", "bool", "byte", "short", "int", "long", "float", "double"}


def is_str_represents_valid_integer_value(stringVal):
    """
    Checks if given string represents acceptable integer value
    Returns true if string contains perfect double.
    Eg: "128.0"

    :param stringVal: string
    :return: boolean
    """
    try:
        if float(stringVal).is_integer():
            return True
        return False
    except ValueError:
        return False

def is_str_represents_float_value(stringVal):
    """
    Checks if given string represents float value
    Returns true if string contains only float value.
    Eg: "128.24"

    :param stringVal: string
    :return: boolean
    """
    try:
        if float(stringVal):
            return True
        return False
    except ValueError:
        return False

class DataType(Enum):

    """
    Classify datatypes used.
    """

    STRING = "string"
    LONG = "long"
    DOUBLE = "double"
    FLOAT = "float"
    GEO_POINT = "geo_point"
    BOOLEAN = "boolean"
    DATE = "date"
    TEXT = "text"
    DECIMAL = "decimal"
    INTEGER = "int"


# For conversion of Sparql/Gremlin type name to ES format
# Any type without a key here will be considered as text in ES.
# All non-floating numeric types will be stored as long in ES, all floating types will be stored as double in ES.
datatypeMapping = {
    'bool': DataType.BOOLEAN.value,
    'boolean': DataType.BOOLEAN.value,

    'int': DataType.LONG.value,
    'integer': DataType.LONG.value,
    'byte': DataType.LONG.value,
    'short': DataType.LONG.value,
    'nonnegativeinteger': DataType.LONG.value,
    'nonpositiveinteger': DataType.LONG.value,
    'negativeinteger': DataType.LONG.value,
    'unsignedbyte': DataType.LONG.value,
    'unsignedint': DataType.LONG.value,
    'unsignedlong': DataType.LONG.value,
    'unsignedshort': DataType.LONG.value,
    'long': DataType.LONG.value,

    'decimal': DataType.DOUBLE.value,
    'float': DataType.DOUBLE.value,
    'double': DataType.DOUBLE.value,

    'datetime': DataType.DATE.value,
    'date': DataType.DATE.value,

    'time': DataType.STRING.value,
    'string': DataType.STRING.value,

    'geo_point': DataType.GEO_POINT.value
}


class DocumentType(Enum):

    """
    Classify Elastic Search Document types
    """

    # Represents a Gremlin vertex document
    VERTEX = "vertex"

    # Represents a Gremlin edge document
    EDGE = "edge"

    # Represents a Sparql RDF Resource
    RDF_RESOURCE = "rdf-resource"


class ElasticSearchDocumentFields(Enum):

    """
    Elastic Search Document field names.
    """

    # Reference to Neptune entity corresponding to document. For Gremlin, it will be Vertex Id  for Vertex document &
    # Edge Id for Edge Document. For Sparql, it will be RDF subject URI.
    ENTITY_ID = "entity_id"

    # Store the Neptune entity type(s). Vertex/Edge label for gremlin. rdf:type for Sparql.
    # Note that Gremlin Vertexes and Sparql can have multiple types.
    ENTITY_TYPE = "entity_type"

    # Classify Elastic Search document. It could be one of vertex/ edge/ rdf-resource
    DOCUMENT_TYPE = "document_type"

    # Nested Field for storing predicates corresponding to Graph vertex / Edge.
    PREDICATES = "predicates"

    """
    Predicate Value Nested Object Fields
    """
    # Store Value for the given predicate. Vertex/Edge property value for Gremlin. RDF object value for Sparql.
    # Note one predicate can have multiple values stored as a nested object list.
    VALUE = "value"

    # Neptune specific datatype corresponding to predicate value. Datatype will not be present for
    # string values.
    DATATYPE = "datatype"

    # Specific to Sparql language. Stores language information corresponding to RDF LangString Literal.
    # Ex: For "test"@en (value=test, language=en)
    LANGUAGE = "language"

    # Specific to Sparql language. Stores Named Graph information. Present if Triple/ NQuad belongs to a Named Graph.
    GRAPH = "graph"


# Default Index Mapping. Dynamic Templates make sure datatype, graph, language fields present in
# nested object for predicate are not analyzed.
MAPPINGS = {
    "dynamic_templates": [
        {
            "datatype": {
                "path_match": "predicates.*.datatype",
                "mapping": {
                    "type": "keyword",
                    "index": "true"
                }
            }
        },
        {
            "graph": {
                "path_match": "predicates.*.graph",
                "mapping": {
                    "type": "keyword",
                    "index": "true"
                }
            }
        },
        {
            "language": {
                "path_match": "predicates.*.language",
                "mapping": {
                    "type": "keyword",
                    "index": "true"
                }
            }
        },
        {
            "value": {
                "path_match": "predicates.*.value",
                "mapping": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                }
            }
        }
    ]
}

def is_valid_float_value(str):
    """
    Checks if string contains valid float value
    """
    try:
        float(str)
    except ValueError:
        return False
    return True

def get_date_time_from_millis(time_in_millis):

    """
    Converts time in milliseconds to ISO format datetime string

    :param time_in_millis: time in milliseconds
    :return: Date time String in ISO format
    """

    return dt.fromtimestamp(time_in_millis / 1000.0).isoformat("T", "milliseconds")


def __index_settings__():

    """
    Generates Index settings with details of replicas & shards

    :return: Index Settings
    """

    return {
        "number_of_shards": NO_OF_SHARDS,
        "number_of_replicas": NO_OF_REPLICA
    }


def add_geo_location_mapping(es_client, es_index_mapping_cache):

    """
    Add geo location fields custom mapping for index
    """

    gp_properties_list = get_geopoint_properties()
    for gp_property in gp_properties_list:
        # Add mapping for geoPoint properties if not present in ES.
        if not get_current_mapping_for_predicate(gp_property, es_index_mapping_cache):
            es_index_mapping_cache = add_mapping_to_es(es_client, es_index_mapping_cache, gp_property, "geo_point")


def get_geopoint_properties():

    """
    Generates list of fields to be mapped to ES geo_point

    :return: List of property names
    """

    return [field.strip() for field in GEO_LOCATION_FIELDS.split(",") if field]


def get_excluded_properties():

    """
    Generates set of properties to exclude from being indexed into ElasticSearch

    :return: Set of property names
    """

    return {field.strip() for field in PROPERTIES_TO_EXCLUDE.split(",")}


def get_excluded_datatypes(query_language):

    """
    Get set of Data Types to exclude from being indexed into ElasticSearch

    :param: Query language for records, as specified by the appropriate handler calling this function
    :return: Set of Datatype strings
    """
    types_list = VALID_SPARQL_TYPES if query_language == 'sparql' \
        else VALID_GREMLIN_TYPES

    return {datatype.strip().lower() for datatype in DATATYPES_TO_EXCLUDE.split(",") if datatype in types_list}


def get_url_components(endpoint):

    """
    Extracts hostname & port from URL endpoint.

    :param endpoint: URL Endpoint. Can be of type http://<host>:<port> or <host>:port
    :return: Dict of  of hostname, port
    """

    # pattern to get hostname & port from endpoint url
    pattern = '(?:http.*://)?(?:www\.)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
    match = re.search(pattern, endpoint)
    host = match.group('host')
    port = match.group('port')

    if not port:
        # if no port is present with URL endpoint default to 443
        port = '443'

    return {
        "host": host,
        "port": port,
    }


def validate_es_version(es_client):

    """
    Checks elastic search version. Version less than 7.x is not supported.

    :param es_client:  Elastic Search Client
    """

    try:
        es_info = es_client.info()
        es_version = es_info.get("version").get("number")

        # For old ES versions distribution is not present with version info. For such cases defaulting
        # to "es" distribution.
        es_distribution = es_info.get("version").get("distribution", "es")

        es_version_parts = es_version.split(".")
        es_major_version = int(es_version_parts[0])

        # Bypass version check for new opensearch distributions
        if es_distribution.lower() == OPEN_SEARCH_DISTRIBUTION:
            logger.debug("Skipping Elastic search version check for new opensearch distributions.")
        elif es_major_version < 7:
            raise Exception("Elastic Search version less than 7.x is not supported. Current version - {}"
                            .format(es_version))
    except KeyError:
        raise Exception("Unable to fetch elastic search version from info - {}.".format(str(es_info)))
    except ValueError:
        logger.info("Elastic Search major version is not numeric. Skipping version check. (ES version - {})".format(
            str(es_version)))


def create_index(es_client, index_name):

    """
    Creates Elastic Search Index with specific Mappings & Settings if not already present


    :param es_client:  Elastic Search Client
    :param index_name: Elastic Search Index name
    """

    if es_client.indices.exists(index=index_name):
        logger.info("Elastic Search Index - {} already exist".format(index_name))
    else:
        body = {"settings": __index_settings__()}
        body["mappings"] = MAPPINGS
        es_client.indices.create(index=index_name, body=body)
        logger.info("Created index - {} Successfully with mapping - {}".format(index_name, str(body)))


def generate_es_document_id(record_data):

    """
    Generates Elastic Search document id from Stream Record data.

    :param record_data: Stream Record data
    :return: Elastic Search Document id
    """

    if ID_STR in record_data:
        # For Gremlin usecase
        id_prefix = VERTEX_ID_Prefix if record_data[TYPE_STR] in ["vl", "vp"] else EDGE_ID_PREFIX
        # Appending Prefix to avoid collision between vertex ids & edge ids
        document_id_str = id_prefix + record_data[ID_STR]
    else:
        # For Sparql Usecase
        statement_elements = record_data[ELEMENTS_STR]
        # For Sparql (Subject based) Document - all Predicates ,Objects from triples/nquads are added in
        # same document if subject is same. So Using Subject as document_id_str
        document_id_str = str(statement_elements[SUBJECT])

    return hashlib.md5(document_id_str.encode('utf-8')).hexdigest()  # Have not used SHA as it is more expensive


def add_mapping_to_es(es_client, index_mapping_cache, field_name, field_type=DataType.STRING.value):
    """

    :param es_client:
    :param index_mapping_cache:
    :param field_name:
    :param field_type:
    :return:
    """
    es_client.indices.put_mapping(index='amazon_neptune',
                                  doc_type='_doc',
                                  include_type_name=True,
                                  body=get_es_mapping_for_predicate(field_name, field_type))

    if not index_mapping_cache:
        index_mapping_cache = {}

    local_mapping = get_local_mapping_for_predicate(field_type)
    try:
        index_mapping_cache["amazon_neptune"]["mappings"]["properties"]["predicates"]["properties"][field_name] \
            = local_mapping
    except KeyError:
        index_mapping_cache["amazon_neptune"]["mappings"]["properties"] = {
            "predicates": {
                "properties": {
                    field_name: local_mapping
                }
            }
        }

    logger.debug("Added new mapping for field - {}, mapping - {}".format(field_name, str(local_mapping)))
    return index_mapping_cache


def get_es_type_for_neptune_type(record_type):

    """
    Converts a Gremlin/ SPARQL datatype name to the corresponding ElasticSearch type name.

    :param record_type: Stream record datatype string in Gremlin/ SPARQL format
    :return: Datatype string in ES format
    """

    if not record_type:
        return DataType.STRING.value

    typ = record_type.strip().lower()
    try:
        return datatypeMapping[typ]
    except KeyError:
        return DataType.STRING.value


def get_es_mapping_for_predicate(record_key, record_type):

    """
    Generates new index type mapping based on given predicate key and datatype.

    Provides full mapping hierarchy for field to satisfy format required by ElasticSearch Put Mapping API.

    :param record_type: Stream record property datatype string
    :param record_key: Stream record property key string
    :return: Dict of mappings
    """

    return {
        "properties": {
            "predicates": {
                "properties": {
                    record_key: get_local_mapping_for_predicate(record_type)
                }
            }
        }
    }


def get_local_mapping_for_string_predicate():

    """
    Generates new index string type mapping for local index.

    Provides base mapping value to be inserted with string predicate key into local mapping cache.

    :return: Dict of mappings
    """

    return {
        "properties": {
            "value": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            }
        }
    }


def get_local_mapping_for_predicate(record_type):

    """
    Generates new index type mapping for local index, based on given predicate datatype.

    Provides base mapping value to be inserted with predicate key into local mapping cache.

    :param record_type: Stream record property datatype string
    :return: Dict of mappings
    """

    es_type = get_es_type_for_neptune_type(record_type)

    if es_type == DataType.STRING.value:
        return get_local_mapping_for_string_predicate()

    return {
        "properties": {
            "value": {
                "type": es_type
            }
        }
    }


def get_current_mapping_for_predicate(record_key, local_mapping):

    """
    Returns mapping for the field present in ElasticSearch.

    If no mapping is present for property in Elasticsearch, this method returns None.

    :param local_mapping: Locally cached dict of index mappings
    :param record_key: Stream record predicate key string
    :return: Datatype string or None

    """

    try:
        try:
            field_mapping_type_temp = local_mapping["amazon_neptune"]["mappings"]["properties"]["predicates"]["properties"]

            # when predicate name has "." then mapping is nested
            key_split = record_key.split(".")
            for token in key_split:
                field_mapping_type_temp = field_mapping_type_temp[token]['properties']
            return field_mapping_type_temp["value"]["type"]
        except KeyError:
            return local_mapping["amazon_neptune"]["mappings"]["properties"]["predicates"]["properties"][record_key]["properties"]["value"]["type"]
    except KeyError:
        return None


def convert_to_es_value(es_mapping_type, obj_value):

    """
    Transform  predicate value to corresponding ES equivalent format. For the case where we have mismatching types
    between neptune and es, we try to validate if predicate value can safely converted to ES type.

    :param obj_value: Unmodified Neptune stream record predicate value
    :param es_mapping_type: datatype corresponding to ES.
    :return: Object value in ES format
    """

    if es_mapping_type == 'double':
        # For SPARQL float values might be converted to invalid date values, eg: 1201-01-01
        # In case zero value is returned back
        if (type(obj_value)) == datetime.date:
            return 0.0
        return float(obj_value)
    elif es_mapping_type == 'long':
        """
        If we want to typecast to long for cases such as "111.00", we need to convert to float before calling int function
        as converting string with float value to int directly gives Value Error
        It's safe to do, because at this point we know value is of long type
        """
        return int(float(obj_value))
    elif es_mapping_type == 'date':
        if isinstance(obj_value, datetime.date):
            return obj_value.isoformat()
        elif isinstance(obj_value, datetime.datetime):
            return obj_value.isoformat("T", "milliseconds")
        elif type(obj_value) == int:
            return get_date_time_from_millis(obj_value)
        else:
            # case when str value contains integer/perfect float value, in that case we will get epoch time
            if is_str_represents_valid_integer_value(obj_value):
                return get_date_time_from_millis(float(obj_value))
            try:
                obj_date_val = parse(str(obj_value), False)
            # In case we encounter an error, we return obj_value back instead of abruptly stopping, eg: value is 123.45
            except ParserError:
                return obj_value
            return obj_date_val.isoformat("T", "milliseconds")
    elif es_mapping_type == 'boolean':
        if type(obj_value) == bool:
            return obj_value
        else:
            # Convert value to string, and verify if lowercase value is one of true equivalent
            # For true equivalent values: '1', '1.0', true, "true" return True
            return str(obj_value).lower() in {'true', '"true"', '1', '1.0'}
    else:
        return str(obj_value)
