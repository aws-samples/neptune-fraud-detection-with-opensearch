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


@six.add_metaclass(abc.ABCMeta)
class CredentialProvider:

    """
    Abstract class for accessing Credentials.
    Implementation of this class must ensure credentials are refreshed on expiry.
    """

    @abc.abstractmethod
    def get_access_key(self):
        pass

    @abc.abstractmethod
    def get_secret_key(self):
        pass

    @abc.abstractmethod
    def get_security_token(self):
        pass


class EnvCredentialProvider(CredentialProvider):

    """
    Implementation of Credential Provider. This class reads credential values from environment variables.
    EnvCredentialProvider is suited for scenerios (Lambda Function) where Environment variables are always
    refreshed with valid Credentials.
    """

    def get_access_key(self):
        return os.getenv('AWS_ACCESS_KEY_ID', '')

    def get_secret_key(self):
        return os.getenv('AWS_SECRET_ACCESS_KEY', '')

    def get_security_token(self):
        return os.getenv('AWS_SESSION_TOKEN', '')


# Global variable to access credential_provider. By default EnvCredentialProvider is used.
# Credential Provider can be changed by using set_credential_provider Method
credential_provider = EnvCredentialProvider()


def set_credential_provider(provider):

    """
    Sets global Credential Provider Instance which can be used across the module.

    :param provider:
    """
    global credential_provider
    credential_provider = provider
