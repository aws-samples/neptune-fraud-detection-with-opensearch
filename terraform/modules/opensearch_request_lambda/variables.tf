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

variable "application_name" {
  type        = string
  description = "(Optional) Name of the application."
  default     = "NeptuneStream"
}

variable "index_name" {
  type        = string
  description = "Name of the OpenSearch index to send requests"
  default     = "amazon_neptune"
}

variable "opensearch_endpoint" {
  type        = string
  description = "VPC Domain Endpoint of the OpenSearchCluster."
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet ids to associate the Neptune subnet group."
}

variable "opensearch_sg_id" {
  type        = string
  description = "Security group id of the OpenSearch cluster."
}

variable "iam_role_arn" {
  type        = string
  description = "IAM Role for Lambda to assume that allows sending requests to OpenSearch."
}

variable "lambda_package_type" {
  description = "Lambda deployment package type"
  type        = string
  default     = "Image"
}

variable "docker_file_path" {
  description = "Path to Dockerfile in source package"
  type        = string
  default     = "Dockerfile"
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
