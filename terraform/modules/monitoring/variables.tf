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

variable "create_monitoring_vpc_endpoint" {
  type        = bool
  description = "A Boolean value that defaults to true. You only need to change it to false if you have already created a monitoring endpoint in your VPC."
  default     = true
}

variable "vpc_id" {
  default     = null
  description = "(Required) VPC id to deploy the Monitoring VPC endpoint."
}

variable "ingress_cidr_blocks" {
  default     = null
  description = "List of CIDR blocks that are allowed connection to the Monitoring VPC endpoint."
}

variable "subnet_ids" {
  default     = null
  description = "List of subnet ids to associate the Monitoring VPC endpoint to."
}

variable "application_name" {
  type        = string
  description = "(Optional) Name of the application."
  default     = "NeptuneStream"
}

variable "neptune_reader_endpoint" {
  type        = string
  description = "(Required) A read-only endpoint for the Neptune cluster, automatically load-balanced across replicas."
}

variable "neptune_port" {
  type        = string
  description = "(Required) The port on which the Neptune accepts connections."
}

variable "stream_poller_lambda_name" {
  type        = string
  description = "(Required) Name of the poller lambda function."
}

variable "lease_dynamo_table_id" {
  type        = string
  description = "(Required) Name of the lease Dynamodb table."
}

variable "scheduler_state_machine_arn" {
  type        = string
  description = "(Required) ARN of the scheduler state machine."
}
