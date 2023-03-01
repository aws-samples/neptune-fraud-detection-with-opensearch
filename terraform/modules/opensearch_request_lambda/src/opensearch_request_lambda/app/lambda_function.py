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


import boto3
import logging
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


logger = logging.getLogger(__name__)
logger.setLevel('INFO')

def index_exists(client, index):
    """Checks if given index exists in the cluster."""
    
    indices = client.cat.indices()
    logger.debug(indices)
    position = indices.find(index)
    
    return True if position != -1 else False

def record_count_in_index(client, index):
    """Number of records in the given index."""
    
    response = client.cat.count(index=index)
    count = response.split(" ")[-1].strip()

    return int(count)

def lambda_handler(event, context):
    host = os.environ['OpenSearchDomainEndpoint']
    region = os.environ['Region']
    index_name = os.environ['IndexName']

    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    client = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    logger.debug(client.info())
    if not index_exists(client, index_name):
        logger.info('Index does not exist in OpenSearch cluster. Please run the Poller State Machine to start receiving data from Neptune.')
        return {
            'index_status': 'Not present'
        }
    logger.info('Index %s present in cluster.', index_name)
    
    record_count = record_count_in_index(client, index_name)
    logger.info('Number of records in index: %s', record_count)
    
    records = ''
    if record_count != 0:
        records = client.search(index=index_name)

    result = {
        'index_status': 'Present',
        'number_of_records': str(record_count),
        'records': records
    }

    return result
