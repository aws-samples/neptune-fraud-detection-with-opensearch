# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights served.
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

##############################
# Docker resources & modules #
##############################

provider "docker" {
  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.current.id, data.aws_region.current.name)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}

locals {
  account_id                = data.aws_caller_identity.current.account_id
  create_image_config_block = var.image_config_entry_point != null || var.image_config_command != null || var.image_config_working_directory != null ? [1] : []
  build_args = {
    PYTHON_REPO     = "public.ecr.aws/lambda/python"
    RUNTIME_VERSION = var.runtime_version
    FUNCTION_DIR    = var.function_directory
    TARGETPLATFORM  = "linux/amd64"
    USER            = var.docker_user_name
  }
}

####################
# Lambda resources #
####################

resource "aws_ecr_repository" "check_for_lambda_duplicate_execution_lambda_repo" {
  name                 = "${lower(var.application_name)}-check-for-duplicate-execution-lambda-repo"
  image_tag_mutability = var.image_tag_mutability
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}

resource "docker_registry_image" "check_for_lambda_duplicate_execution_build_image" {
  name = format("%v:%v", aws_ecr_repository.check_for_lambda_duplicate_execution_lambda_repo.repository_url, "v1")

  build {
    context    = "${path.module}/src/check_for_lambda_duplicate_execution"
    dockerfile = var.docker_file_path
    build_args = local.build_args
  }
}

resource "aws_lambda_function" "check_for_lambda_duplicate_execution" {
  function_name                  = "NeptuneCheckForDuplicateExecution"
  description                    = "Checks if there is a state machine already in execution"
  role                           = aws_iam_role.neptune_stream_default_execution_role.arn
  memory_size                    = 128
  timeout                        = 5
  image_uri                      = docker_registry_image.check_for_lambda_duplicate_execution_build_image.name
  package_type                   = var.lambda_package_type
  kms_key_arn                    = var.kms_key_arn
  reserved_concurrent_executions = 10

  dynamic "image_config" {
    for_each = local.create_image_config_block
    content {
      entry_point       = var.image_config_entry_point
      command           = var.image_config_command
      working_directory = var.image_config_working_directory
    }
  }

  environment {
    variables = {
      ApplicationName  = var.application_name
      LeaseTable       = var.lease_dynamo_table
      StateMachineName = var.state_machine_name
    }
  }

  tracing_config {
    mode = "Active"
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.opensearch_sg_id, var.neptune_sg_id]
  }

  dead_letter_config {
    target_arn = var.redrive_queue_arn
  }

}

resource "aws_ecr_repository" "restart_state_machine_execution_lambda_repo" {
  name                 = "${lower(var.application_name)}-restart-state-machine-execution-lambda-repo"
  image_tag_mutability = var.image_tag_mutability
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}

resource "docker_registry_image" "restart_state_machine_execution_build_image" {
  name = format("%v:%v", aws_ecr_repository.restart_state_machine_execution_lambda_repo.repository_url, "v1")

  build {
    context    = "${path.module}/src/restart_state_machine_execution"
    dockerfile = var.docker_file_path
    build_args = local.build_args
  }
}

resource "aws_lambda_function" "restart_state_machine_execution" {
  function_name                  = "NeptuneRestartStateMachineExecution"
  description                    = "Restarts state machine execution"
  role                           = aws_iam_role.neptune_stream_default_execution_role.arn
  memory_size                    = 128
  timeout                        = 5
  image_uri                      = docker_registry_image.restart_state_machine_execution_build_image.name
  package_type                   = var.lambda_package_type
  kms_key_arn                    = var.kms_key_arn
  reserved_concurrent_executions = 10

  dynamic "image_config" {
    for_each = local.create_image_config_block
    content {
      entry_point       = var.image_config_entry_point
      command           = var.image_config_command
      working_directory = var.image_config_working_directory
    }
  }

  environment {
    variables = {
      StateMachineName = var.state_machine_name

    }
  }

  tracing_config {
    mode = "Active"
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.opensearch_sg_id, var.neptune_sg_id]
  }

  dead_letter_config {
    target_arn = var.redrive_queue_arn
  }
}

resource "aws_ecr_repository" "stream_poller_lambda_repo" {
  name                 = "${lower(var.application_name)}-poller-lambda-repo"
  image_tag_mutability = var.image_tag_mutability
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}

resource "docker_registry_image" "stream_poller_build_image" {
  name = format("%v:%v", aws_ecr_repository.stream_poller_lambda_repo.repository_url, "v1")

  build {
    context    = "${path.module}/src/stream_poller_lambda"
    dockerfile = var.docker_file_path
    build_args = local.build_args
  }
}

resource "aws_lambda_function" "stream_poller_lambda" {
  function_name                  = "${var.application_name}PollerLambda"
  description                    = "Loads data from Neptune into OpenSearch"
  role                           = aws_iam_role.neptune_stream_poller_execution_role.arn
  memory_size                    = 2048
  timeout                        = 600
  image_uri                      = docker_registry_image.stream_poller_build_image.name
  package_type                   = var.lambda_package_type
  kms_key_arn                    = var.kms_key_arn
  reserved_concurrent_executions = 10

  dynamic "image_config" {
    for_each = local.create_image_config_block
    content {
      entry_point       = var.image_config_entry_point
      command           = var.image_config_command
      working_directory = var.image_config_working_directory
    }
  }

  environment {
    variables = {
      AdditionalParams             = jsonencode(merge(var.stream_poller_additional_params, { "ElasticSearchEndpoint" = var.opensearch_endpoint }))
      Application                  = var.application_name
      IAMAuthEnabledOnSourceStream = true
      LeaseTable                   = var.lease_dynamo_table
      LoggingLevel                 = "INFO"
      MaxPollingInterval           = 600
      MaxPollingWaitTime           = 60
      NeptuneStreamEndpoint        = "https://${var.neptune_reader_endpoint}:${var.neptune_port}/gremlin/stream"
      StreamRecordsBatchSize       = 100
      StreamRecordsHandler         = "neptune_to_es.neptune_gremlin_es_handler.ElasticSearchGremlinHandler"
    }
  }

  tracing_config {
    mode = "Active"
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.opensearch_sg_id, var.neptune_sg_id]
  }

  dead_letter_config {
    target_arn = var.redrive_queue_arn
  }
}
