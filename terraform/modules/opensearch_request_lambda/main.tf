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

##################################
# Opensearch resources & modules #
##################################

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "2.16.0"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_ecr_authorization_token" "token" {}

provider "docker" {
  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.current.id, data.aws_region.current.name)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  build_args = {
    PYTHON_REPO     = "public.ecr.aws/lambda/python"
    RUNTIME_VERSION = var.runtime_version
    FUNCTION_DIR    = var.function_directory
    TARGETPLATFORM  = "linux/amd64"
    USER            = var.docker_user_name
  }
}

################################
# Docker & AWS Lambda Creation #
################################

resource "aws_ecr_repository" "opensearch_request_lambda_repo" {
  name                 = "${lower(var.application_name)}-opensearch-request-lambda-repo"
  image_tag_mutability = var.image_tag_mutability
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}

resource "docker_registry_image" "opensearch_request_lambda_build_image" {
  name = format("%v:%v", aws_ecr_repository.opensearch_request_lambda_repo.repository_url, "v1")

  build {
    context    = "${path.module}/src/opensearch_request_lambda"
    dockerfile = var.docker_file_path
    build_args = local.build_args
  }
}

resource "aws_lambda_function" "opensearch_request_lambda" {
  function_name                  = join("", [var.application_name, "OpenSearchRequestLambda"])
  description                    = "Sends a search request to OpenSearch to verify data is being synced with Neptune."
  role                           = var.iam_role_arn
  memory_size                    = 128
  timeout                        = 5
  image_uri                      = docker_registry_image.opensearch_request_lambda_build_image.name
  package_type                   = var.lambda_package_type
  kms_key_arn                    = var.kms_key_arn
  reserved_concurrent_executions = 10

  environment {
    variables = {
      OpenSearchDomainEndpoint = var.opensearch_endpoint
      Region                   = data.aws_region.current.name
      IndexName                = var.index_name
    }
  }

  tracing_config {
    mode = "Active"
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.opensearch_sg_id]
  }

  dead_letter_config {
    target_arn = var.redrive_queue_arn
  }
}
