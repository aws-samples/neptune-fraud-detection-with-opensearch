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

import re
import datetime
from dateutil.parser import parse
from decimal import Decimal
from neptune_to_es.es_helper import DataType, is_str_represents_valid_integer_value

lang_regex = re.compile(r"^[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*$")


def validate(value, es_datatype):
    """
    Validates if a given predicate value can be converted to a given es datatype.

    :param value:  predicate value to be validated against given datatype
    :param es_datatype: reference es datatype for which predicate value is validated
    :return: boolean
    """
    if value is None:
        return False
    elif es_datatype == DataType.STRING.value or es_datatype == DataType.TEXT.value:
        return True
    elif es_datatype not in es_type_to_validator:
        return False
    else:
        try:
            return es_type_to_validator[es_datatype](value) or False
        except ValueError:
            return False


def validate_language(language):
    """
    Validates if SPARQL language tag matches regex format.

    :param language: language tag from SPARQL langString literal
    :return: boolean True or False
    """
    if re.match(lang_regex, language):
        return True
    else:
        return False


def validate_geopoint(record_value):
    """
    Validates geo_point value for a valid format and latitude/ longitude ranges.
     Format for geo_point -> "[lat],[lon]"
    latitude range: -90 to 90
    longitude range: -180 to 180

    :param record_value: predicate value to be validated for geo_point datatype
    :return: boolean True or False
    """

    geopoint_components = record_value.replace(" ", "").split(",")
    try:
        if len(geopoint_components) == 2:
            if (abs(float(geopoint_components[0])) <= 90) and (abs(float(geopoint_components[1])) <= 180):
                return True
    except ValueError:
        return False
    return False


def validate_boolean(value):
    """
    Validates if predicate value can be safely converted to a boolean type. Below are the cases for safe conversion:
    1) if value is of type bool
    2) if value is string and lower case of value is one among {'true', '"true"', 'false', '"false"', '0', '1'}

    Ex:
    True - valid
    False - valid
    "abc" - invalid
    "1" - valid
    "0" - valid
    "TRUE" - valid
    "FaLsE" - valid
    123 - invalid
    1.0 - valid
    0.0 - valid
    1 - valid
    0 - valid
    "1.0" - valid
    "0.0" - valid
    "-0" -valid
    "-0.0" - valid

    :param value: predicate value to be validated for boolean datatype
    :return: boolean True or False
    """
    if type(value) == bool:
        return True
    # handle case when 0, 1, 0.0, 1,0 is supplied as string
    elif isinstance(value, str) and value.lower() in {'true', '"true"', 'false', '"false"', '0', '1', '0.0', '1.0', '-0', '-0.0'}:
        return True
    # handle case when 0 or 1 is supplied as int
    elif isinstance(value, int) and value in {0, 1}:
        return True
    # handle case when 0.0 or 1.0 is supplied as float
    elif isinstance(value, float) and value in {0.0, 1.0}:
        return True


def validate_double(value):
    """
    Validates if predicate value can be safely converted to a double type. Below are few rules:
    1) if value is of type bool - invalid
    2) if value is of type date/datetime - invalid
    3) if float conversion of value result in TypeError or ValueError - invalid

    Ex:
    123 - valid
    12.3 - valid
    "111" - valid
    "11.1" - valid
    "abc" - invalid
    True - invalid
    date(2016-01-01) - invalid

    :param value: predicate value to be validated for double datatype
    :return: boolean True or False
    """

    if type(value) == bool or isinstance(value, datetime.datetime) \
            or isinstance(value, datetime.date):
        return False

    try:
        if float(value) or float(value) == 0.0:
            # for float(0.0) this code path is not reached, as 0.0 is false in python
            return True
    except (TypeError, ValueError):
        return False

    return False


def validate_long(value):
    """
    Validates if predicate value can be safely converted to a long type. Below are few rules:
    1) if value is of type bool - invalid
    2) if value is of type date/datetime - invalid
    3) if value is of type float representing a integer value - valid
    4) if value is of type decimal representing int value - valid
    5) if value is of type String representing floating value - invalid  ( need to explicitly handle this as
    int(value) will not detect this)
    6) if int conversion of value result in TypeError or ValueError - invalid

    Ex:
    123 - valid
    12.3 - invalid
    Decimal(11.0) - valid
    "111" - valid
    "11.1" - invalid
    "abc" - invalid
    True - invalid
    date(2016-01-01) - invalid

    :param value: predicate value to be validated for long datatype
    :return: boolean True or False
    """

    if type(value) == bool or isinstance(value, datetime.datetime) \
            or isinstance(value, datetime.date) or (isinstance(value, float) and not value.is_integer()) \
            or (isinstance(value, str) and not is_str_represents_valid_integer_value(value)) or (isinstance(value, Decimal) and value % 1 != 0):
        return False

    try:
        """
        If we want to typecast to long for cases such as "111.00", we need to convert to float before calling int function
        as converting string with float value to int directly gives Value Error
        It's safe to do for all types, because at this point we know value is of long type
        """
        return int(float(value)).bit_length() <= 63
    except (TypeError, ValueError):
        return False


def validate_date(value):
    """
    Validates if predicate value can be safely converted to a date type. Below are few rules:
    1) if value instance of date/datetime - valid
    2) if value is of type string which can be parsed to a valid datetime format.

    Ex:
    Date(2016-01-01) - valid
    "2016-01-01" - valid
    "2003-09-25T10:49:41" - valid
    "2003-09-25T10:49" - valid
    "2003-09-25T10" - valid
    "20030925T104941-0300" - valid ( ISO format without seperators)
    "20030925T104941" - valid
    "2003-Sep-25" - valid
    "Sep-25-2003" - valid
    "2003.Sep.25" - valid
    "2003/09/25" - valid
    "2003 Sep 25" - valid
    "Wed, July 10, '96" - valid
    "Tuesday, April 12, 1952 AD 3:30:42pm PST" - valid
    "abcdef" - invalid
    123 - valid, converted to epoch time
    12.45 - invalid
    True - invalid

    :param value: predicate value to be validated for Date datatype
    :return: boolean True or False
    """

    if isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
        return True
    else:
        try:
            if (type(value) == float):
                return False
            # integer can be converted to epoch time
            if type(value) == int or (isinstance(value, str) and is_str_represents_valid_integer_value(value)):
                return True
            parse(str(value), False)
            return True
        except ValueError:
            return False

es_type_to_validator = {
     'boolean': validate_boolean,
     'double': validate_double,
     'date': validate_date,
     'long': validate_long,
     'geo_point': validate_geopoint
}
