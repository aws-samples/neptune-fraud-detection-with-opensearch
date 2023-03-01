# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights served.
# SPDX-License-Identifier: MIT-0
#  
# Permission is hereby granted, free of charge, to any person taining a copy of this
# software and associated documentation files (the oftware"), to deal in the Software
# without restriction, including without limitation the rights  use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies  the Software, and to
# permit persons to whom the Software is furnished to do so.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY ND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF RCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL E AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, ETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN NNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#################
# IAM Resources #
#################

###############
# Stream role #
###############

data "aws_iam_policy_document" "neptune_stream_default_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "neptune_stream_default_policy_permissions" {
  statement {
    sid = "AllowLambdaInvoke"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = ["arn:aws:lambda:*:*:function:*"]
    effect    = "Allow"
  }
  statement {
    sid = "AllowGlobalAccess"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords"
    ]
    resources = ["arn:aws:xray:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
    effect    = "Allow"
  }
  statement {
    sid = "AllowCreateCloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:*:*:log-group:*",
      "arn:aws:logs:*:*:log-group:*:log-stream:*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowDynamoDBActions"
    actions = [
      "dynamodb:UpdateItem"
    ]
    resources = [
      "arn:aws:dynamodb:*:*:table/*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowStateMachineActions"
    actions = [
      "states:ListExecutions",
      "states:StartExecution",
      "states:DescribeExecution"
    ]
    resources = [
      "arn:aws:states:*:*:execution:*:*",
      "arn:aws:states:*:*:stateMachine:*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowEC2CreateNetworkInterface"
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:DetachNetworkInterface"
    ]
    resources = [
      "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*/*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowEC2DescribeNetworkInterfaces"
    actions = [
      "ec2:DescribeNetworkInterfaces"
    ]
    resources = [
      "*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowKMSDecryptAction"
    actions = [
      "kms:Decrypt"
    ]
    resources = [
      var.kms_key_arn
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowSQSActions"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [
      var.redrive_queue_arn
    ]
    effect = "Allow"
  }
}

resource "aws_iam_role" "neptune_stream_default_execution_role" {
  name               = "NeptuneStreamDefaultExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.neptune_stream_default_assume_role.json
}

resource "aws_iam_policy" "neptune_stream_default_policy" {
  name        = "NeptuneStreamPollerPolicy"
  path        = local.path
  description = "Neptune Stream Default Policy"
  policy      = data.aws_iam_policy_document.neptune_stream_default_policy_permissions.json
}

resource "aws_iam_policy_attachment" "neptune_stream_default_execution_policy_attachment" {
  name       = "NeptuneStreamPollerPolicyAttachment"
  roles      = [aws_iam_role.neptune_stream_default_execution_role.name]
  policy_arn = aws_iam_policy.neptune_stream_default_policy.arn
}

###############
# Poller Role #
###############

data "aws_iam_policy_document" "neptune_stream_default_policy" {
  statement {
    sid = "AllowOpenSearch"
    actions = [
      "es:ESHttpDelete",
      "es:ESHttpGet",
      "es:ESHttpHead",
      "es:ESHttpPost",
      "es:ESHttpPut"
    ]
    resources = ["arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${var.opensearch_domain}/*"]
    effect    = "Allow"
  }
  statement {
    sid = "AllowLambdaInvoke"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = ["arn:aws:lambda:*:*:function:*"]
    effect    = "Allow"
  }
  statement {
    sid = "AllowLogActions"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:*:*:log-group:*",
      "arn:aws:logs:*:*:log-group:*:log-stream:*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowDynamoDBActions"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Scan",
      "dynamodb:UpdateItem",
      "dynamodb:DescribeTable",
      "dynamodb:DeleteItem"
    ]
    resources = [
      "arn:aws:dynamodb:*:*:table/*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowStateMachineActions"
    actions = [
      "states:ListExecutions",
      "states:StartExecution",
      "states:DescribeExecution"
    ]
    resources = [
      "arn:aws:states:*:*:execution:*:*",
      "arn:aws:states:*:*:stateMachine:*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowKMSDecryptAction"
    actions = [
      "kms:Decrypt"
    ]
    resources = [
      var.kms_key_arn
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowCloudWatchMetricsAllow"
    actions = [
      "cloudwatch:putMetricData"
    ]
    resources = [
      "*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowNeptuneDB"
    actions = [
      "neptune-db:*"
    ]
    resources = [
      "arn:aws:neptune-db:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.neptune_cluster_resource_id}/*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowEC2CreateNetworkInterface"
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:DetachNetworkInterface",
    ]
    resources = [
      "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*/*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowEC2DescribeNetworkInterfaces"
    actions = [
      "ec2:DescribeNetworkInterfaces"
    ]
    resources = [
      "*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowCreateCloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:*:*:log-group:*",
      "arn:aws:logs:*:*:log-group:*:log-stream:*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowSQSActions"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [
      var.redrive_queue_arn
    ]
    effect = "Allow"
  }
}

resource "aws_iam_role" "neptune_stream_poller_execution_role" {
  name               = var.neptune_poller_lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.neptune_stream_default_assume_role.json
}

resource "aws_iam_policy" "neptune_stream_poller_es_policy" {
  name        = "neptune_stream_poller_es_policy"
  path        = local.path
  description = "Neptune Stream Poller Lambda IAM Policy"
  policy      = data.aws_iam_policy_document.neptune_stream_default_policy.json
}

resource "aws_iam_policy_attachment" "neptune_stream_poller_es_execution_policy_attachment" {
  name       = "NeptuneStreamPollerAttachment"
  roles      = [aws_iam_role.neptune_stream_poller_execution_role.name]
  policy_arn = aws_iam_policy.neptune_stream_poller_es_policy.arn
}
