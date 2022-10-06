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

variable "vpc_id" {
  default     = null
  description = "(Required) VPC id to deploy the DynamoDB VPC endpoint."
}

variable "route_table_ids" {
  default     = null
  description = "(Required) List of route tables to associate the DynamoDB VPC endpoint."
}

variable "application_name" {
  type        = string
  description = "(Optional) Name of the application."
  default     = "NeptuneStream"
}

variable "create_dynamodb_vpc_endpoint" {
  type        = bool
  description = "A Boolean value that defaults to true. You only need to change it to false if you have already created a DynamoDB endpoint in your VPC."
  default     = true
}

variable "kms_key_arn" {
  type        = string
  description = "The ARN of the KMS key to use for server-side encryption."
}
