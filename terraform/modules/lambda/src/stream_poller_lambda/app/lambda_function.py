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

import logging
import boto3

from config_provider import config_provider
from commons import *
from stream_records_processor import StreamRecordsProcessor
from metrics_publisher import MetricsPublisher
from ddb_helper import DDBLeaseManager


# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)


# global variables
metrics_publisher_client = MetricsPublisher()
stream_records_processor = StreamRecordsProcessor()
dynamodb = boto3.resource('dynamodb', region_name=config_provider.region)
lease_manager = DDBLeaseManager(dynamodb.Table(config_provider.lease_table_name))


def get_or_create_lease():

    """
    Get or create Lease in Lease Table.
    :return: Lease Object from Dynamo DB Table
    """
    lease_manager.create_lease_if_not_exists(
        {
            'leaseKey': config_provider.application_name,
            'checkpointSubSequenceNumber': '0',
            'checkpoint': '0',
            'leaseOwner': 'nobody',
            'lastUpdateTime': current_milli_time()
        }
    )

    return lease_manager.get_lease(config_provider.application_name)


def lambda_handler(event, context):

    """
    Main Lambda handler
    This is invoked when Lambda is called.
    This lambda function do below steps sequentially:
    1. Take Lease
    2. Poll for records from Stream until no records or 90% of Lambda Execution time is reached
    3. Stream records are passed to appropriate handlers. If no records are found lambda exists &
     pass wait_time to state machine
    4. Metrics are published to Cloud watch
    """

    lease = get_or_create_lease()
    lease['leaseOwner'] = config_provider.application_name
    logger.info("Taking lease for {} ....".format(lease['leaseOwner']))
    lease = lease_manager.take_lease(lease)

    # Time to stop Continuous polling from Stream if not otherwise stopped
    execution_end_time = current_milli_time() + int(round(0.9 * config_provider.max_polling_interval * 1000))
    wait_time = event['iterator']['wait_time']
    try:
        while current_milli_time() < execution_end_time:
            # case when no more records are present in stream
            if not stream_records_processor.process_with_metrics(lease, lease_manager, metrics_publisher_client):
                wait_time = get_wait_time(config_provider.max_polling_wait_time, wait_time)
                # wait_time can be zero when set to do continuous polling. For continuous polling no need to wait.
                if wait_time > 0:
                    logger.info("Waiting for {} seconds before next Polling.".format(str(wait_time)))
                    break
            else:
                # case when there are more records present in stream. No need to wait.
                wait_time = 0

    except Exception as e:
        logger.error("Error Occurred while processing records - {}.".format(str(e)))
        raise e
    finally:
        logger.info("Evicting lease - {}".format(str(lease)))
        lease_manager.evict_lease(lease)

    index = event['iterator']['index'] + 1
    response = {
        'index': index,
        'continue': index < event['iterator']['count'],
        'count': event['iterator']['count'],
        'wait_time': wait_time
    }

    logger.info("Finished running Lambda function handler. Passing Response to next step - {}".format(response))
    return response
