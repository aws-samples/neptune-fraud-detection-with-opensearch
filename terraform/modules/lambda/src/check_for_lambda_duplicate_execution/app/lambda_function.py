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

import json
import boto3
import os
import time
from botocore.exceptions import ClientError


client = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb', os.environ['AWS_REGION'])
lease_table = dynamodb.Table(os.environ['LeaseTable'])


def get_current_time():
     return int(round(time.time() * 1000))


def evict_open_lease():
    print('Evicting any open lease ...')
    try:
        lease_table.update_item(
            Key={'leaseKey': os.environ['ApplicationName']},
            UpdateExpression='SET leaseOwner = :NOBODY,' +
                             ' lastUpdateTime= :lastUpdateTimeVal',
            ConditionExpression='leaseKey = :leaseKey and leaseOwner <> :NOBODY',
            ExpressionAttributeValues={':lastUpdateTimeVal': get_current_time(),
                                       ':NOBODY': 'nobody',
                                       ':leaseKey': os.environ['ApplicationName']
                                       },
            ReturnValues='ALL_NEW')
        print('Evicted open lease')
    except ClientError as e:
        if e.response['Error']['Code'] in ['ConditionalCheckFailedException', 'ResourceNotFoundException']:
            print('No open lease found')
        else:
            raise


def lambda_handler(event, context):
    account_number = context.invoked_function_arn.split(':')[4]
    partition= context.invoked_function_arn.split(':')[1]
    state_machine_arn = 'arn:' + partition + ':states:' + os.environ['AWS_REGION']  + ':' + account_number  + ':stateMachine:' + os.environ['StateMachineName']
    print ('Getting currently running execution list for state machine - {}'.format(state_machine_arn))
    response = client.list_executions(
         stateMachineArn=state_machine_arn,
         statusFilter='RUNNING'
    )
    ignore_execution_id_list = [event['id']]
    if 'parentId' in event:
        ignore_execution_id_list.append(event['parentId'])
    
    print('Executions to Ignore: Ids[{}]'.format(ignore_execution_id_list))
    execution_count = 0
    for execution in response['executions']:
        rs = client.describe_execution(executionArn=execution['executionArn'])
        input = json.loads(rs['input'])
        if input['id'] not in ignore_execution_id_list:
            execution_count += 1
    print ('Number of Other Executions with status running : {}'.format(execution_count))
    already_running = execution_count > 0
    
    if not already_running:
        evict_open_lease()
    return {'alreadyRunning':  already_running}
    