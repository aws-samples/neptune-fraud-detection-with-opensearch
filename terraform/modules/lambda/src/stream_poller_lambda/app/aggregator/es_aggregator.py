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

from aggregator.aggregator import Aggregator
from neptune_to_es import es_helper
from commons import *
import collections
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ElasticSearchAggregator(Aggregator):

    """
    Aggregates Stream records in a bundle for optimizing Elastic Search bulk updates. A single update request
    can be created & sent to Elastic Search for the bundle of records. Aggregator can execute
    in either Default mode or Optimized mode.

    In default mode, records from one transaction will be aggregated while in Optimized mode records over
    multiple transactions will be aggregated which can give optimized performance at a cost of breaking
    Transaction Semantics.
    Example of how Transaction Semantics can break for Optimized mode : (Reference Gremlin)
    Transaction 1 -> Add Vertex V1, Add Vertex V2.
    Transaction 2 -> Add Property to Vertex V1 , Add Property to Vertex V2

    In optimized mode records for vertex V1 creation & its property addition are bundled together. So ,
    when bundled records for V1 are used to create a single query it might happen that V1 property is added
    before Vertex V2 is created. Thus, breaking the Transaction Semantics.

    Both the modes retain add & remove operation orders. Ex:
    Below are Stream Records for same Vertex
    Record1 ->OP : Add Property foo
    Record2-> OP : Add Property bar
    Record3 -> OP : Remove Property bar
    Record4 -> OP : Add Property baz

    Three Bundles will be created in the order as below:
    [Record1, Record2]
    [Record3]
    [Record4]
    """

    # Literals for Aggregator Modes
    OPTIMIZED_MODE = "optimized"
    DEFAULT_MODE = "default"

    def __init__(self, mode=DEFAULT_MODE):
        self.mode = mode

    def __generate_key__(self, record):

        """
        Generates Key used to reference a bundle of records based on Aggregator Mode.

        :param record: Stream Record
        :return: Record Key
        """
        record_id = es_helper.generate_es_document_id(record[DATA_STR])
        if self.mode == self.DEFAULT_MODE:
            return "{}_{}".format(record[EVENT_ID_STR][COMMIT_NUM_STR], record_id)
        else:
            return record_id

    def __create_record_set_entry__(self, record_data, operation_type):

        """
        Creates new entry for appending to the aggregated bundle

        :param record_data: Stream Record Data
        :param operation_type: Operation type for Stream Record. Ex: ADD_vl, REMOVE_e
        :return: Json for New Record Entry
        """

        return {
            OPERATION_STR: operation_type,
            RECORDS_STR: [record_data]
        }

    def __create_aggregate_entry(self, record_key, records_map, record_data, operation_type):

        """
        Creates New Aggregate Bundle for a given Record key.

        :param record_key: Key to store data in Records Bundle Map
        :param records_map:  Records Bundle Map
        :param record_data: Stream Record Data
        :param operation_type: Operation type for Stream Record. Ex: ADD_vl, REMOVE_e
        """

        records_map[record_key] = {
            CURRENT_INDEX_STR: 0,
            CURRENT_OP_STR: operation_type,
            RECORDS_SET_STR: [self.__create_record_set_entry__(record_data, operation_type)]
        }

    def __append_record_set__(self, record_key, records_map, record_data, operation_type):

        """
        Appends new Record to an existing aggregated bundle for a given record key

        :param record_key: Key to store data in Records Bundle Map
        :param records_map: Records Bundle Map
        :param record_data: Stream Record Data
        :param operation_type: Operation type for Stream Record. Ex: ADD_vl, REMOVE_e
        """

        records_map[record_key][CURRENT_OP_STR] = operation_type
        records_map[record_key][CURRENT_INDEX_STR] += 1
        records_map[record_key][RECORDS_SET_STR]\
            .append(self.__create_record_set_entry__(record_data, operation_type))

    def aggregate_records(self, records):

        """
        Aggregates records for a given set of Stream Records.

        :param records:  Stream Records
        :return: Aggregated Records Map
        """
        logger.info("Aggregating Stream Records for Optimization")
        records_map = collections.OrderedDict()
        for record in records:
            record_data = record[DATA_STR]
            operation_type = record[OPERATION_STR]

            # For Gremlin Usecase Operation_type will be combination of both Operation (ADD or REMOVE)
            # and Type (e, ep, vl, vp). Type is only present in Gremlin Stream Record
            if TYPE_STR in record_data:
                operation_type = "{}_{}".format(record[OPERATION_STR], record_data[TYPE_STR])
            record_key = self.__generate_key__(record)
            if record_key not in records_map:
                self.__create_aggregate_entry(record_key, records_map, record_data, operation_type)
            elif records_map[record_key][CURRENT_OP_STR] != operation_type:
                self.__append_record_set__(record_key, records_map, record_data, operation_type)
            else:
                current_index = records_map[record_key][CURRENT_INDEX_STR]
                records_map[record_key][RECORDS_SET_STR][current_index][RECORDS_STR].append(record_data)
        logger.info("Finished Aggregating Stream Records")
        return records_map
