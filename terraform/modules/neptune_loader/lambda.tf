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

provider "docker" {
  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.current.id, data.aws_region.current.name)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}


locals {
  account_id     = data.aws_caller_identity.current.account_id
  ecr_address    = aws_ecr_repository.repo.repository_url
  ecr_repo       = aws_ecr_repository.repo.id
  image_tag      = coalesce(var.image_tag, formatdate("YYYYMMDDhhmmss", timestamp()))
  ecr_image_name = format("%v:%v", local.ecr_address, local.image_tag)
  source_path    = "${path.module}/src/neptune_loader_from_s3"
  build_args = {
    PYTHON_REPO     = "public.ecr.aws/lambda/python"
    RUNTIME_VERSION = var.runtime_version
    FUNCTION_DIR    = var.function_directory
    TARGETPLATFORM  = "linux/amd64"
    USER            = var.docker_user_name
  }
  function_name = "${var.application_name}LoaderFromS3Lambda"
}

######################################
# Neptune Loader resources & modules #
######################################

resource "aws_ecr_repository" "repo" {
  name                 = "${lower(var.application_name)}-repo"
  image_tag_mutability = var.image_tag_mutability
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}

resource "docker_registry_image" "build_image" {
  name = local.ecr_image_name

  build {
    context    = local.source_path
    dockerfile = var.docker_file_path
    build_args = local.build_args
  }
}

data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "neptune_loader_from_s3_execution_role" {
  name               = "NeptuneLoaderLambdaExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}

data "aws_iam_policy_document" "neptune_es_stream_poller_policy_json" {
  statement {
    sid = "AllowXrayAccess"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords"
    ]
    resources = ["arn:aws:xray:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
    effect    = "Allow"
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
    sid = "AllowLogActions"
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
    sid = "AllowCloudWatchMetricsActions"
    actions = [
      "cloudwatch:putMetricData"
    ]
    resources = [
      "*"
    ]
    effect = "Allow"
  }
  statement {
    sid = "AllowNeptuneActions"
    actions = [
      "neptune-db:*"
    ]
    resources = [
      "arn:aws:neptune-db:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.neptune_cluster_resource_id}/*"
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
      "arn:aws:sqs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.sqs_queue_name}",
      var.redrive_queue_arn
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
}

resource "aws_iam_policy" "neptune_es_stream_poller_policy" {
  name        = "neptune_es_stream_poller_policy"
  path        = "/"
  description = "My test policy"
  policy      = data.aws_iam_policy_document.neptune_es_stream_poller_policy_json.json
}

resource "aws_iam_policy_attachment" "neptune_es_stream_poller_policy_attachment" {
  name       = "neptune_stream_poller_es_execution_policy"
  roles      = [aws_iam_role.neptune_loader_from_s3_execution_role.name]
  policy_arn = aws_iam_policy.neptune_es_stream_poller_policy.arn
}

resource "aws_lambda_function" "neptune_loader_from_s3" {
  function_name                  = local.function_name
  description                    = "Loads data from S3 into Neptune"
  role                           = aws_iam_role.neptune_loader_from_s3_execution_role.arn
  memory_size                    = 256
  timeout                        = 15
  image_uri                      = docker_registry_image.build_image.name
  package_type                   = var.lambda_package_type
  kms_key_arn                    = var.kms_key_arn
  reserved_concurrent_executions = 10

  image_config {
    entry_point       = var.image_config_entry_point
    command           = var.image_config_command
    working_directory = var.image_config_working_directory
  }

  environment {
    variables = {
      DATABASE_LOADER_ENDPOINT_URL = "https://${var.neptune_cluster_endpoint}:${var.neptune_port}/loader"
      S3_SOURCE_BUCKET             = "s3://${aws_s3_bucket.neptune_s3_bucket.id}"
      FILE_FORMAT                  = "csv"
      NEPTUNE_IAM_ROLE_ARN         = var.neptune_cluster_iam_role_arn
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.neptune_sg_id]
  }

  tracing_config {
    mode = "Active"
  }

  dead_letter_config {
    target_arn = var.redrive_queue_arn
  }
}

resource "aws_lambda_permission" "allow_sqs" {
  statement_id   = "AllowExecutionFromSQS"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.neptune_loader_from_s3.function_name
  principal      = "sqs.amazonaws.com"
  source_arn     = aws_sqs_queue.sqs_queue.arn
  source_account = local.account_id
}

resource "aws_lambda_event_source_mapping" "sqs_to_lambda" {
  event_source_arn = aws_sqs_queue.sqs_queue.arn
  function_name    = aws_lambda_function.neptune_loader_from_s3.arn
}
