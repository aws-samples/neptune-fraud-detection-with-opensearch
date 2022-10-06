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
import uuid


client = boto3.client('stepfunctions')


def lambda_handler(event, context):
    account_number = context.invoked_function_arn.split(':')[4]
    partition= context.invoked_function_arn.split(':')[1]
    state_machine_arn = 'arn:' + partition + ':states:' + os.environ['AWS_REGION']  + ':' + account_number  + ':stateMachine:' + os.environ['StateMachineName']
    input = {
             'id': str(uuid.uuid4()),
             'detail-type': 'Started by Lambda',
             'source': 'aws.lambda',
             'account': account_number,
             'region': os.environ['AWS_REGION'],
             'resource': context.invoked_function_arn,
             'restart': True
            }
    if 'id' in event:
        input['parentId'] = event['id']
    client.start_execution(
         stateMachineArn=state_machine_arn,
         input=json.dumps(input)
    )
    return input
