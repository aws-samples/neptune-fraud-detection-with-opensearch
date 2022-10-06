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

import requests
import logging
import importlib
from urllib.parse import urlparse

from commons import *

import neptune_sigv4_signer
from config_provider import config_provider

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)


def __get_handler_instance__(handler_name):

    """
    Get Handler instance given a handler name with module
    :param handler_name: the handler class name with module.
    :return: Handler instance

    """
    try:
        parts = handler_name.rsplit('.', 1)
        module = importlib.import_module(parts[0])
        cls = getattr(module, parts[1])
        return cls()
    except Exception as e:
        logger.error("Error Occurred while creating Handler instance for {} - {}.".format(handler_name, str(e)))
        raise e


# Global variables
stream_records_handler = __get_handler_instance__(config_provider.stream_records_handler_name)


def __get_query_language__(stream_endpoint):

    """
    Derive Query Language from Stream Endpoint.

    :param stream_endpoint: Stream Endpoint
    :return: Return Neptune Query Language
    """
    if "gremlin" in stream_endpoint.lower():
        return GREMLIN
    elif "sparql" in stream_endpoint.lower():
        return SPARQL
    else:
        logger.error("Error getting Query Language - Invalid Stream Endpoint {}".format(stream_endpoint))
        raise Exception("Invalid Stream Endpoint {}".format(stream_endpoint))


class StreamRecordsProcessor:

    def __get_stream_lag_time(self, commit_time):

        """
        Method to calculate by how many milliseconds stream poller is behind Head of Stream.
        Used to publish Cloud watch metrics

        :param commit_time: commit time from current Stream log
        :return: diff in milliseconds between Current time and Stream log Commit time
        """

        return int(current_milli_time() - commit_time)

    def read_records(self, limit, commit_num='0', op_num='0'):

        """
        Read records from stream after a given commit_num & op_num.
        This method use AFTER_SEQUENCE_NUMBER iteratorType as query parameter for getting records from
        Stream after a given (commit_num, op_num).

        If commit_num & op_num is zero, records are read from beginning of Stream using TRIM_HORIZON
        iteratorType as query parameter

        If IAMAuth is enabled on Neptune Stream Cluster, http request is signed using Sigv4_signer.

        :param limit: Number of records to be read from stream
        :param commit_num: Commit Number for Stream Record
        :param op_num: Operation Number for Stream Record
        :return: List of records from Stream
        """

        payload = {'limit': limit, 'commitNum': commit_num, 'opNum': op_num,
                   'iteratorType': 'AFTER_SEQUENCE_NUMBER'}
        starting_commit_num = int(commit_num)

        # Reading Stream records very first time
        if commit_num == '0' and op_num == '0':
            payload = {'limit': limit, 'iteratorType': 'TRIM_HORIZON'}
            starting_commit_num = None
        headers = {}

        # Adding Authentication headers for IAM Auth Enabled Cluster
        if config_provider.iam_auth_enabled_on_source_stream:
            query_type = '{}_{}'.format(__get_query_language__(config_provider.neptune_stream_endpoint), 'stream')
            headers = neptune_sigv4_signer.get_signed_header(urlparse(config_provider.neptune_stream_endpoint).netloc,
                                                             'GET', query_type, payload)

        logger.debug("Querying Neptune Stream with endpoint - {}, payload - {}"
                     .format(config_provider.neptune_stream_endpoint, str(payload)))
        return self._fetch_and_validate_stream_records(payload, headers=headers,
                                                       starting_commit_num=starting_commit_num)

    def process(self, limit, commit_num, op_num):

        """
        Read records from Stream for a given set of commit_num, op_num, limit parameters and pass these records to
        the configured Handler for further processing.

        Handler for processing stream records can be set in ConfigProvider using parameter
        "stream_records_handler_name".

        If there are no more records in stream, response form handler will be None else appropriate response
        from handler is returned

        :param limit: Number of records to be read from stream
        :param commit_num: Commit Number for Stream Record
        :param op_num: Operation Number for Stream Record
        :return: a tuple of (Response from handler, Stream Log)
        """

        logger.info("Reading records from stream. Reference event id (commitNum, OpNum) - {} , {} and limit - {}"
                    .format(commit_num, op_num, limit))
        stream_log = self.read_records(limit, commit_num, op_num)

        if stream_log is None:
            # No records in Stream
            return None, stream_log

        logger.info("Start processing Stream Records...")
        # Calling Handler to further process Stream Records
        return stream_records_handler.handle_records(stream_log), stream_log

    def process_with_metrics(self, lease, lease_manager, metrics_publisher_client):

        """
        Read records from Stream based on lease object and pass these records to
        the configured Handler for further processing.

        This method also update lease with commit num, operation num of last successful record processed in
        lease table and also publish Metrics to cloud watch.

        Need to pass instance of ddb_helper.DDBLeaseManager and metrics_publisher.MetricsPublisher to this method

        :param lease: lease object from Dynamo DB Table which keeps track of the records that
                      have already been processed from Stream using Checkpoint
        :param lease_manager: instance of ddb_helper.DDBLeaseManager
        :param metrics_publisher_client: instance of metrics_publisher.MetricsPublisher
        :return: boolean : True means there could be more records in Stream, False means no more records in Stream
        """

        results, stream_log = self.process(config_provider.stream_records_batch_size, lease['checkpoint'],
                                           lease['checkpointSubSequenceNumber'])

        if results is None:
            # No records in Stream

            logger.info("Publishing Stream Metrics data...")
            metrics_publisher_client.publish_metrics([metrics_publisher_client.generate_record_processed_metrics(0),
                                                      metrics_publisher_client.generate_stream_lag_metrics(0)])
            logger.info("No more stream records to process.")
            return False  # Stop Continuous Poll from Stream and wait for some time

        # When Stream records are processed in small chunks by handler, handle_records method returns
        # series of results one-by-one on Demand using Python Generators.
        # Each iteration will compute result object lazily which can further be used to update Lease
        # and publish Metrics
        for result in results:
            lease['checkpointSubSequenceNumber'] = result.last_op_num
            lease['checkpoint'] = result.last_commit_num
            logger.info("Updating Lease with checkpoint, subSequenceNumber ({}, {})"
                        .format(lease['checkpoint'], lease['checkpointSubSequenceNumber']))
            lease_manager.update_lease(lease)
            logger.info("Publishing Stream Records Processed Metrics data...")
            metrics_publisher_client \
                .publish_metrics([metrics_publisher_client
                                 .generate_record_processed_metrics(result.records_processed)])
            logger.info("Finished publishing data to Metrics")

        logger.info("Publishing Stream Lag Metrics data...")
        # Publish Lag Metrics
        metrics_publisher_client.publish_metrics([metrics_publisher_client
                                                 .generate_stream_lag_metrics
                                                  (self.__get_stream_lag_time(stream_log[LAST_TXN_TIMESTAMP_STR]))])

        logger.info("Finished processing Stream records. Last Processed event id (commitNum, OpNum) - {} , {}"
                    .format(stream_log[LAST_EVENT_ID][COMMIT_NUM_STR], stream_log[LAST_EVENT_ID][OP_NUM_STR]))

        return True  # No wait required when records are found

    def _fetch_and_validate_stream_records(self, payload, headers=None, starting_commit_num=None):
        """
        Fetch stream records by making http request to streams endpoint and Throws exception if stream response has
        missing commits

        :param payload: Stream http request parameters
        :param headers: Http request headers
        :return: Object: Stream response
        """
        stream_response = self._make_streams_http_call(payload, headers)
        if stream_response is None:
            return None

        records = stream_response.get('records')
        first_missing_commit_num = self._find_first_missing_commit_in_stream(records,
                                                                             starting_commit_num=starting_commit_num)
        if first_missing_commit_num is not None:
            raise Exception("Found missing commit in the Stream - {}. Note: It is an intermittent issue and "
                            "should auto-resolve in next lambda runs. \nStream response - {}"
                            .format(first_missing_commit_num, stream_response))
        return stream_response

    @staticmethod
    def _find_first_missing_commit_in_stream(records, starting_commit_num=None):
        """
        Check if there are any missing commits in the list of stream records and
        return first missing commit number if exists

        :param records: Stream records
        :return: integer: None if no commit is missing else First missing commit number
        """
        if records is None or len(records) == 0:
            return None

        prev_commit_num = starting_commit_num

        for current_record in records:

            current_commit_num = current_record.get('eventId').get('commitNum')
            # prev_commit_num will be None when Stream call is made with TRIM_HORIZON as iteratorType.
            # Use first record as the prev_commit_num
            if prev_commit_num is None:
                prev_commit_num = current_commit_num
                continue

            commit_diff = current_commit_num - prev_commit_num

            # Two records' commit numbers should not differ by more than one
            if commit_diff > 1:
                # prev_commit_num + 1 is the missing commit if commit_diff is more than 1
                return prev_commit_num + 1
            prev_commit_num = current_commit_num

        # No missing records found
        return None

    @staticmethod
    def _make_streams_http_call(payload, headers=None):
        """
        Make Http call to Neptune streams endpoint to fetch stream records

        :param payload: Http request payload
        :param headers: Http request headers
        :return: object: None if no records are found else StreamResponse
        """
        with requests.get(config_provider.neptune_stream_endpoint, params=payload, headers=headers) as response:
            if response.status_code == 200:
                # Successfully retrieved records from Stream
                return response.json()
            elif response.status_code == 404:
                # Either No records present or reached end of Stream Case
                logger.info("No more Records...")
                return None
            else:
                raise Exception("Error Occurred while reading data from Stream. - {}".format(response.json()))
