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

###################
# Input variables #
###################

variable "vpc_id" {
  type        = string
  description = "VPC id to deploy the Neptune cluster in if not creatig a sample one."
}

variable "application_name" {
  type        = string
  description = "(Optional) Name of the application."
  default     = "NeptuneStream"
}

variable "create_s3_vpc_endpoint" {
  type        = bool
  description = "A Boolean value that defaults to true. You only need to change it to false if you have already created an S3 endpoint in your VPC."
  default     = true
}

######################
# S3 input variables #
######################

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN to be used with S3, Lambda, and SQS."
}

variable "ssl_policy_enabled" {
  type        = bool
  default     = true
  description = "A boolean flag to enable/disable enforcing SSL requests."
}

variable "block_public_access_s3_enabled" {
  type        = bool
  default     = true
  description = "A boolean flag to enable/disable Public Access Block configuration to S3."
}

variable "force_destroy_enabled" {
  type        = bool
  default     = false
  description = "A boolean flag to enable/disable object deletion so that the bucket can be destroyed without error. These objects are not recoverable."
}

variable "bucket_versioning_enabled" {
  type        = bool
  default     = false
  description = "A boolean flag to enable/disable S3 bucket versioning."
}

##########################
# Lambda input variables #
##########################

variable "neptune_cluster_resource_id" {
  type        = string
  description = "(Optional) If your Neptune DB cluster is using IAM authentication, set this parameter to the cluster resource ID."
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet ids to associate the Neptune subnet group."
}

variable "neptune_sg_id" {
  type        = string
  description = "Security group id of the Neptube cluster."
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

variable "image_tag" {
  description = "Image tag to use. If not provided date will be used"
  type        = string
  default     = null
}

variable "lambda_package_type" {
  description = "Lambda deployment package type"
  type        = string
  default     = "Image"
}

variable "image_config_entry_point" {
  description = "The ENTRYPOINT for the docker image"
  type        = list(string)
  default     = []
}

variable "image_config_command" {
  description = "The CMD for the docker image"
  type        = list(string)
  default     = []
}

variable "image_config_working_directory" {
  description = "The working directory for the docker image"
  type        = string
  default     = null
}

variable "neptune_cluster_iam_role_arn" {
  description = "The IAM Role ARN associated to the Neptune cluster that allows access to S3 for bulk loading"
  type        = string
  default     = null
}

variable "neptune_cluster_endpoint" {
  type        = string
  description = "The main endpoint of the Neptune cluster"
}

variable "neptune_port" {
  type        = string
  description = "(Required) The port on which the Neptune accepts connections."
}

####################
# Docker Variables #
####################

variable "source_path" {
  description = "Path to folder containing application code"
  type        = string
  default     = null
}

variable "docker_file_path" {
  description = "Path to Dockerfile in source package"
  type        = string
  default     = "Dockerfile"
}

variable "build_args" {
  description = "A map of Docker build arguments."
  type        = map(string)
  default     = {}
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

variable "use_public_docker_repo" {
  description = "Boolean variable to indicate if base python image should be pulled from the public docker registry instead. Not recommended."
  type        = bool
  default     = true
}

variable "graph_load_data_format" {
  description = "File format to use with Amazon Bulk Loader to ingest data. Gremlin load data format must be csv."
  type        = string
  default     = "csv"
}

variable "nodes_folder_prefix" {
  description = "Folder prefix where files with node information will be stored."
  type        = string
  default     = "nodes/"
}

variable "edges_folder_prefix" {
  description = "Folder prefix where files with edge information will be stored."
  type        = string
  default     = "edges/"
}

variable "docker_user_name" {
  description = "Name for the Docker user container"
  type        = string
  default     = "lambdacontainer"
}

#######
# SQS #
#######

variable "sqs_queue_name" {
  description = "The name of the queue."
  type        = string
  default     = "NeptuneStreamLoader"
}

variable "visibility_timeout_seconds" {
  description = "(Optional) The visibility timeout for the queue. An integer from 0 to 43200 (12 hours). The default for this attribute is 30."
  type        = number
  default     = 30
}

variable "redrive_queue_arn" {
  description = "ARN of the SQS queue to use in DLQ configuration"
  type        = string
}
