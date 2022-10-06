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

import boto3
from config_provider import config_provider


# Global Instances
cloudwatch_client = boto3.client('cloudwatch', region_name=config_provider.region)


class MetricsPublisher:

    """
    Generate and publish Cloud Watch metrics for Neptune Stream Poller.
    Metrics are data about the performance of systems which in turn help in detailed monitoring.
    For Stream Poller, system is publishing data for two key metrics:

    Number of Records Processed - This metric capture how many records from Neptune Stream are
                                  successfully processed per unit of time. This Metric can
                                  be used to analyse Throughput.
    Lag Time for Stream Poller - This metric capture by how many milliseconds Stream poller is lagging  behind
                                 the latest commit on Neptune Source Instance.

    Both the Metrics are Published to AWS Cloud Watch using Metrics Publisher Class.
    """

    def __init__(self):
        self.nameSpace = 'AWS/Neptune'

    def __generate_metrics__(self, metric_name, dimension_name, dimension_value, unit, value):

        """
        Generates metrics json object which will be used to publish metrics

        :param metric_name: Name of Cloud watch Metrics
        :param dimension_name:  Dimension  name associated with cloud watch metrics
        :param dimension_value: Dimension value associated with cloud watch metrics
        :param unit: Unit of data published to cloud watch
        :param value:  Value of data published to cloud watch
        :return: Json object to create Metrics
        """

        return {
                 'MetricName': metric_name,
                 'Dimensions': [
                     {
                         'Name': dimension_name,
                         'Value': dimension_value
                     },
                 ],
                 'Unit': unit,
                 'Value': value
        }

    def publish_metrics(self, metrics):

        """
        Publishes Metrics on cloudwatch using cloudwatch client.

        :param metrics: Lists of Metrics to be published
        """

        cloudwatch_client.put_metric_data(MetricData=metrics, Namespace=self.nameSpace)

    def generate_record_processed_metrics(self, count):

        """
        Generates metrics for number of records processed by stream
        :param count: Count of number of records processed
        :return: Cloud watch Metrics object
        """

        return self.__generate_metrics__(str(config_provider.application_name) + ' - Stream Records Processed',
                                         'Neptune Stream', config_provider.neptune_stream_endpoint, 'Count', int(count))

    def generate_stream_lag_metrics(self, time_in_millis):

        """
        Generates metrics for lag time of stream poller
        :param time_in_millis: Lag time in Milliseconds
        :return: Cloud watch Metrics object
        """
        return self.__generate_metrics__(str(config_provider.application_name) + ' - Stream Lag from Neptune DB',
                                         'Neptune Stream', config_provider.neptune_stream_endpoint, 'Milliseconds',
                                         time_in_millis)
