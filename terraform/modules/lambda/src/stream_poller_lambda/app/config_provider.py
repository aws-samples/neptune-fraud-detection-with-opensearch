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

import abc
import six
import os
import json
from enum import Enum


class ConfigParamNameEnum(Enum):

    """
       Configuration parameters name.
       These parameters are needed to be added to config map with a valid value while initializing Config Provider.
    """

    # AWS Region
    REGION = "region"

    # Number of records read from Stream in One Poll
    STREAM_RECORDS_BATCH_SIZE = "stream_records_batch_size"

    # Maximum wait time in seconds between two successive polling from stream
    MAX_POLLING_WAIT_TIME = "max_polling_wait_time"

    # Period in seconds for which we can continuously poll stream for records
    MAX_POLLING_INTERVAL = "max_polling_interval"

    # Application name used as a reference for creating lease & publishing cloudwatch metrics
    APPLICATION_NAME = "application_name"

    # Dynamo DB Table name used for managing lease for stream
    LEASE_TABLE_NAME = "lease_table_name"

    # Neptune Stream Endpoint.
    NEPTUNE_STREAM_ENDPOINT = "neptune_stream_endpoint"

    # Handler name to process Stream Records.
    STREAM_RECORDS_HANDLER_NAME = "stream_records_handler_name"

    # Flag to check if IAM Auth is enabled on Neptune Cluster
    IAM_AUTH_ENABLED_ON_SOURCE_STREAM = "iam_auth_enabled_on_source_stream"

    # Json String with additional parameters needed by Handler to process
    HANDLER_ADDITIONAL_PARAMS = "handler_additional_params"

    # Process Logging Level
    LOGGING_LEVEL = "logging_level"


@six.add_metaclass(abc.ABCMeta)
class ConfigProvider:

    """
    Abstract Class for managing process Configuration.
    Sub-classes needs to implement load method for setting up the configuration map.
    """

    def __init__(self):

        # Dictionary object for storing Configuration
        self.config_map = self.load()

    @abc.abstractmethod
    def load(self):

        """
        Abstract Method to load Configuration & sets them on the config_map object.

        Subclasses should implement this method to load Configuration in desired manner

        :return: dictionary object with configuration values
        """
        pass

    def get_config_value(self, config_name, default=None):

        """
        Returns config value for a given configuration parameter. This method throws exception
        if config value is not present or no default value is specified.

        :param default: Default value to be returned in case config value is not present.
        :param config_name: Config Parameter name for which value needs to be fetched
        :return: Value for given config name if present else throw KeyError Exception
        """
        if config_name in self.config_map:
            return self.config_map[config_name]
        elif default is not None:
            return default
        else:
            raise KeyError("No Configuration present for key - {}".format(config_name))

    @property
    def region(self):
        return self.get_config_value(ConfigParamNameEnum.REGION.value)

    @property
    def stream_records_batch_size(self):
        return int(self.get_config_value(ConfigParamNameEnum.STREAM_RECORDS_BATCH_SIZE.value))

    @property
    def max_polling_wait_time(self):
        return int(self.get_config_value(ConfigParamNameEnum.MAX_POLLING_WAIT_TIME.value, 10))

    @property
    def max_polling_interval(self):
        return int(self.get_config_value(ConfigParamNameEnum.MAX_POLLING_INTERVAL.value, 600))

    @property
    def application_name(self):
        return self.get_config_value(ConfigParamNameEnum.APPLICATION_NAME.value, '')

    @property
    def lease_table_name(self):
        return self.get_config_value(ConfigParamNameEnum.LEASE_TABLE_NAME.value, '')

    @property
    def neptune_stream_endpoint(self):
        return self.get_config_value(ConfigParamNameEnum.NEPTUNE_STREAM_ENDPOINT.value)

    @property
    def stream_records_handler_name(self):
        return self.get_config_value(ConfigParamNameEnum.STREAM_RECORDS_HANDLER_NAME.value)

    @property
    def iam_auth_enabled_on_source_stream(self):
        return bool(self.get_config_value(ConfigParamNameEnum.IAM_AUTH_ENABLED_ON_SOURCE_STREAM.value, 'false'))

    @property
    def logging_level(self):
        return self.get_config_value(ConfigParamNameEnum.LOGGING_LEVEL.value, 'INFO')

    @property
    def handler_additional_params(self):

        # Handler Additional Params value in Config Map must be Json Object
        return self.get_config_value(ConfigParamNameEnum.HANDLER_ADDITIONAL_PARAMS.value, {})

    def get_handler_additional_param(self, key, default=''):
        if key in self.handler_additional_params:
            return self.handler_additional_params.get(key)
        else:
            return default


class EnvConfigProvider(ConfigProvider):

    """
    Sub-Class of ConfigProvider. This class loads Config values from system Environment variables
    """

    def load(self):

        """
        Implementation of parent class method. This method loads Configuration from environment variables &
        sets them to config_map object. All the below configurations are mandatory to be set some valid value to
        run the process.

        :return: config value Map
        """
        return {
            ConfigParamNameEnum.REGION.value: os.environ['AWS_REGION'],
            ConfigParamNameEnum.STREAM_RECORDS_BATCH_SIZE.value: os.environ['StreamRecordsBatchSize'],
            ConfigParamNameEnum.MAX_POLLING_WAIT_TIME.value: int(os.environ['MaxPollingWaitTime']),
            ConfigParamNameEnum.MAX_POLLING_INTERVAL.value: int(os.environ['MaxPollingInterval']),
            ConfigParamNameEnum.APPLICATION_NAME.value: os.environ['Application'],
            ConfigParamNameEnum.LEASE_TABLE_NAME.value: os.environ['LeaseTable'],
            ConfigParamNameEnum.NEPTUNE_STREAM_ENDPOINT.value: os.environ['NeptuneStreamEndpoint'],
            ConfigParamNameEnum.STREAM_RECORDS_HANDLER_NAME.value: os.environ['StreamRecordsHandler'],
            ConfigParamNameEnum.IAM_AUTH_ENABLED_ON_SOURCE_STREAM.value:
                  os.getenv('IAMAuthEnabledOnSourceStream', 'false') != 'false',
            ConfigParamNameEnum.LOGGING_LEVEL.value: os.getenv('LoggingLevel', 'INFO'),
            ConfigParamNameEnum.HANDLER_ADDITIONAL_PARAMS.value: json.loads(
                  os.getenv('AdditionalParams', '')) if os.getenv('AdditionalParams', '') else {}
        }


# Global variable to access config_provider. By default EnvConfigProvider is used.
# Config Provider can be changed by using set_config_provider Method
config_provider = EnvConfigProvider()


def set_config_provider(provider):

    """
    Sets global Config Provider Instance which can be used across the module.

    :param provider: Config Provider instance
    """

    global config_provider
    config_provider = provider
