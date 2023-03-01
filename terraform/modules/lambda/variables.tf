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

############################################
# Input variables for AWS Lambda functions #
############################################

variable "application_name" {
  type        = string
  description = "(Optional) Name of the application."
  default     = "NeptuneStream"
}

variable "lease_dynamo_table" {
  type        = string
  description = "(Required) Name of the application."
}

variable "state_machine_name" {
  type        = string
  description = "(Required) Name of the State Machine."
  default     = "NeptuneStreamStreamPoller"
}

variable "stream_poller_additional_params" {
  type        = map(string)
  description = "(Required) Additional parameters for stream poller lambda."
  default = {
    "NumberOfShards"          = "5"
    "NumberOfReplica"         = "1"
    "IgnoreMissingDocument"   = "true"
    "ReplicationScope"        = "all"
    "GeoLocationFields"       = ""
    "DatatypesToExclude"      = ""
    "PropertiesToExclude"     = ""
    "EnableNonStringIndexing" = "true"
  }
}

variable "opensearch_endpoint" {
  type        = string
  description = "(Required) OpenSearch domain-specific endpoint used to submit index, search, and data upload requests."
}

variable "opensearch_domain" {
  type        = string
  description = "(Required) Name of the OpenSearch domain."
}

variable "neptune_cluster_resource_id" {
  type        = string
  description = "(Optional) If your Neptune DB cluster is using IAM authentication, set this parameter to the cluster resource ID."
}

variable "neptune_reader_endpoint" {
  type        = string
  description = "(Required) A read-only endpoint for the Neptune cluster, automatically load-balanced across replicas."
}

variable "neptune_port" {
  type        = string
  description = "(Required) The port on which the Neptune accepts connections."
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet ids to associate the Neptune subnet group."
}

variable "opensearch_sg_id" {
  type        = string
  description = "Security group id of the OpenSearch cluster."
}

variable "neptune_sg_id" {
  type        = string
  description = "Security group id of the Neptube cluster."
}

variable "neptune_poller_lambda_role_name" {
  type        = string
  description = "(Optional) IAM Role of the lambda function that performs polls on neptune cluster."
  default     = "NeptuneStreamPollerExecutionRole"
}

variable "image_tag" {
  description = "Image tag to use. If not provided date will be used"
  type        = string
  default     = null
}

variable "runtime_version" {
  description = "Python runtime version to use with lambda container image."
  type        = string
  default     = "3.9"
}

variable "function_directory" {
  description = "Function directory containing files."
  type        = string
  default     = "/app"
}

variable "image_tag_mutability" {
  type    = string
  default = "IMMUTABLE"
}

variable "scan_on_push" {
  description = "Indicates whether images are scanned after being pushed to the repository"
  type        = bool
  default     = true
}

variable "docker_file_path" {
  description = "Path to Dockerfile in source package"
  type        = string
  default     = "Dockerfile"
}

variable "lambda_package_type" {
  description = "Lambda deployment package type"
  type        = string
  default     = "Image"
}

variable "image_config_entry_point" {
  description = "The ENTRYPOINT for the docker image"
  type        = list(string)
  default     = null
}

variable "image_config_command" {
  description = "The CMD for the docker image"
  type        = list(string)
  default     = null
}

variable "image_config_working_directory" {
  description = "The working directory for the docker image"
  type        = string
  default     = null
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN to be used with S3, Lambda, and SQS."
}

variable "redrive_queue_arn" {
  description = "ARN of the SQS queue to use in DLQ configuration"
  type        = string
}

variable "docker_user_name" {
  description = "Name for the Docker user container"
  type        = string
  default     = "lambdacontainer"
}
