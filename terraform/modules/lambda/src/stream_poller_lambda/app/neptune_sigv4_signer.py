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

import sys
import datetime
import hashlib
import hmac
import urllib
import logging
from config_provider import config_provider
from credential_provider import credential_provider

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)

# Signer Literal
SERVICE = 'neptune-db'

CANONICAL_URI_MAP = {
    "sparql": "/sparql",
    "gremlin": "/gremlin",
    "gremlin_stream": "/gremlin/stream",
    "sparql_stream": "/sparql/stream"
}

SIGNED_HEADERS = 'host;x-amz-date'


def __normalize_query_string__(query_parameters):
    """
    Normalize and sort query parameters.
    :param query_parameters: Query string parameters
    :return: Sorted Query string parameters
    """

    kv = (list(map(str.strip, s.split("=")))
          for s in query_parameters.split('&')
          if len(s) > 0)
    normalized = '&'.join('%s=%s' % (p[0], p[1] if len(p) > 1 else '')
                          for p in sorted(kv))
    return normalized


def __sign__(key, msg):
    """
    Creates hash-based message authentication codes (HMACs)

    :param key: Secret Key
    :param msg: Array of bytes to be hashed
    :return:
    """

    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def __get_signature_key__(key, date_stamp, region_name, service_name):
    """
    Derives signing key from AWS Secret Access key using date, region and service.

    :param key: AWS Secret Access key
    :param date_stamp: Date used in the hashing process is in the format YYYYMMDD
    :param region_name: AWS Region
    :param service_name: Service name
    :return: Signing key
    """
    k_date = __sign__(('AWS4' + key).encode('utf-8'), date_stamp)
    k_region = __sign__(k_date, region_name)
    k_service = __sign__(k_region, service_name)
    k_signing = __sign__(k_service, 'aws4_request')
    return k_signing


def urlencode_payload(payload):
    """
    Convert payload to URLEncoded  value.

    :param payload: Request Payload
    :return: Urlencoded value
    """

    # do the encoding => quote_via=urllib.parse.quote is used to map " " => "%20"
    request_parameters = urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)
    request_parameters = request_parameters.replace('%27', '%22')
    return request_parameters


def __get_canonical_uri__(query_type):
    """
    Returns Canonical URI based on query type. Query Type can have values like
    sparql, gremlin, sparql_stream, gremlin_stream

    :param query_type: Type of Neptune Query
    :return: Canonical URI string
    """
    return CANONICAL_URI_MAP.get(query_type)


def __create_canonical_request__(host, method, query_type, request_parameters, amzdate):
    """
    Creates canonical version of request for Signature Version 4 based on
    https://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html

    :param host: Host for Request
    :param method: HTTP request method GET, PUT, POST, etc.
    :param query_type: Neptune query_type. Used to get Canonical URI
    :param request_parameters: URLEncoded HTTP request parameters
    :param amzdate: Date for your request. This is passed to request as a part of header.
    :return:  Canonical Request

    """

    # Step 1 is to define the verb (GET, POST, etc.)

    # Coming as parameter - method

    # Step 2: is to define the canonical_uri

    canonical_uri = __get_canonical_uri__(query_type)

    # Step 3: Create the canonical query string. In this example (a GET request),
    # request parameters are in the query string. Query string values must
    # be URL-encoded (space=%20). The parameters must be sorted by name.
    # For this example, the query string is pre-formatted in the request_parameters variable.

    if method == 'GET':
        canonical_querystring = __normalize_query_string__(request_parameters)
    elif method == 'POST':
        canonical_querystring = ''
    else:
        print('Request method is neither "GET" nor "POST", something is wrong here.')
        sys.exit()

    # Step 4: Create the canonical headers and signed headers. Header names
    # must be trimmed and lowercase, and sorted in code point order from
    # low to high. Note that there is a trailing \n.
    canonical_headers = 'host:' + host + '\n' + 'x-amz-date:' + amzdate + '\n'

    # Step 5: Create the list of signed headers. This lists the headers
    # in the canonical_headers list, delimited with ";" and in alpha order.
    # Note: The request can include any headers; canonical_headers and
    # signed_headers lists those that you want to be included in the
    # hash of the request. "Host" and "x-amz-date" are always required.

    # Declared as Global Variable

    # Step 6: Create payload hash (hash of the request body content). For GET
    # requests, the payload is an empty string ("").
    if method == 'GET':
        post_payload = ''
    elif method == 'POST':
        post_payload = request_parameters
    else:
        print('Request method is neither "GET" nor "POST", something is wrong here.')
        sys.exit()

    payload_hash = hashlib.sha256(post_payload.encode('utf-8')).hexdigest()

    # Step 7: Combine elements to create canonical request.
    canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring \
                        + '\n' + canonical_headers + '\n' + SIGNED_HEADERS + '\n' + payload_hash
    return canonical_request


def get_signed_header(host, method, query_type, payload, region=config_provider.region):
    """
    Returns Headers for Signed Request. This method follows steps from below AWS Doc.
    https://docs.aws.amazon.com/general/latest/gr/sigv4_signing.html

    :param host: Host for Request
    :param method: HTTP request method GET, PUT, POST, etc.
    :param query_type: Neptune query_type. Used to get Canonical URI
    :param payload: Request Payload
    :param region: if request shoudl be signed for any other region.
    :return: Headers for Signed request
    """

    logger.debug("Creating signed request ...")
    # ************* REQUEST VALUES *************

    request_parameters = urlencode_payload(payload)

    # ************* TASK 1: CREATE A CANONICAL REQUEST *************

    # Create a date for headers and the credential string.
    t = datetime.datetime.utcnow()
    amzdate = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')  # Date w/o time, used in credential scope
    canonical_request = __create_canonical_request__(host, method, query_type, request_parameters, amzdate)

    # ************* TASK 2: CREATE THE STRING TO SIGN*************
    # Match the algorithm to the hashing algorithm you use, either SHA-1 or
    # SHA-256 (recommended)
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = datestamp + '/' + region + '/' + SERVICE + '/' + 'aws4_request'
    string_to_sign = algorithm + '\n' + amzdate + '\n' + credential_scope + '\n' + hashlib.sha256(
        canonical_request.encode('utf-8')).hexdigest()

    # ************* TASK 3: CALCULATE THE SIGNATURE *************
    # Create the signing key using the function defined above.
    signing_key = __get_signature_key__(credential_provider.get_secret_key(), datestamp,
                                        region, SERVICE)

    # Sign the string_to_sign using the signing_key
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # ************* TASK 4: ADD SIGNING INFORMATION TO THE REQUEST *************
    # The signing information can be either in a query string value or in
    # a header named Authorization. This code shows how to use a header.
    # Create authorization header and add to request headers
    authorization_header = algorithm + ' ' + 'Credential=' + credential_provider.get_access_key() + '/' \
                           + credential_scope + ', ' + 'SignedHeaders=' + SIGNED_HEADERS + ', ' \
                           + 'Signature=' + signature

    # The request can include any headers, but MUST include "host", "x-amz-date",
    # and (for this scenario) "Authorization". "host" and "x-amz-date" must
    # be included in the canonical_headers and signed_headers, as noted
    # earlier. Order here is not significant.
    # Python note: The 'host' header is added automatically by the Python 'requests' library.
    return {'x-amz-date': amzdate, 'Authorization': authorization_header,
            'x-amz-security-token': credential_provider.get_security_token()}
