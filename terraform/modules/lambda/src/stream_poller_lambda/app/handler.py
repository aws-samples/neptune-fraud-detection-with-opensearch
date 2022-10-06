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


class HandlerResponse:
    """
    Model for Storing Handler Response.

    This Class has three attributes:
    last_op_num - Op_num for last stream record processed
    last_commit_num - Commit number for last stream record processed
    records_processed - Number of Stream Records Processed
    """

    def __init__(self, last_op_num, last_commit_num, records_processed):
        self.last_op_num = last_op_num
        self.last_commit_num = last_commit_num
        self.records_processed = records_processed


@six.add_metaclass(abc.ABCMeta)
class AbstractHandler:

    """
    Abstract class for  Handler
    """

    @abc.abstractmethod
    def handle_records(self, stream_log):

        """
        Abstract Method for Processing Stream Records. This method should return a Python Generator Object
        wrapped around HandlerResponse using Python yield statement { yield HandlerResponse(......) }

        :param stream_log:
        :return: Returns Python Generator object wrapped around HandlerResponse using yield statement
        """
        pass
