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
import os
import requests
import sys
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from requests.structures import CaseInsensitiveDict
from types import SimpleNamespace

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def prepare_loader_request(database_url, payload):
    service = 'neptune-db'
    method = 'POST'

    access_key = os.environ['AWS_ACCESS_KEY_ID']
    secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
    region = os.environ['AWS_REGION']
    session_token = os.environ['AWS_SESSION_TOKEN']
    
    creds = SimpleNamespace(
        access_key=access_key, secret_key=secret_key, token=session_token, region=region,
    )

    request = AWSRequest(method=method, url=database_url, data=payload)
    SigV4Auth(creds, service, region).add_auth(request)

    logger.info('## Request header')
    logger.info(request.headers)

    return request

def prepare_loader_payload():
    payload = {
        "source" : os.environ['S3_SOURCE_BUCKET'],
        "format": os.environ['FILE_FORMAT'],
        "iamRoleArn" : os.environ['NEPTUNE_IAM_ROLE_ARN'],
        "region": os.environ['AWS_REGION'],
        "failOnError" : "FALSE",
        "parallelism" : "MEDIUM",
        "updateSingleCardinalityProperties" : "FALSE",
        "queueRequest" : "TRUE",
        "dependencies" : []
    }

    logger.debug('## Payload')
    logger.debug(payload)
    
    return payload

def lambda_handler(event, context):
    database_url = os.environ['DATABASE_LOADER_ENDPOINT_URL']
    payload = prepare_loader_payload()
    request = prepare_loader_request(database_url, payload)    
    response = requests.post(database_url, headers=request.headers, data=payload)

    return response.json()
