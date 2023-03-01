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

variable "vpc_id" {
  default     = null
  description = "VPC id to deploy the Neptune cluster in if not creatig a sample one."
}

variable "subnet_ids" {
  default     = [""]
  description = "List of subnet ids to associate the Neptune subnet group."
}

variable "domain_name" {
  type        = string
  description = "(Required) Name of the domain."
  default     = ""
}

variable "opensearch_version" {
  type        = string
  description = "(Optional) Version of Opensearch to deploy. Defaults to 1.2"
  default     = "OpenSearch_1.2"
}

variable "encrypt_at_rest" {
  type        = bool
  description = "(Optional) Configuration block for encrypt at rest options. Only available for certain instance types. Detailed below."
  default     = "true"
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN to be used with OpenSearch."
}

variable "ebs_enabled" {
  type        = bool
  description = "(Required) Whether EBS volumes are attached to data nodes in the domain."
  default     = "true"
}

variable "volume_size" {
  type        = number
  description = "(Required if ebs_enabled is set to true.) Size of EBS volumes attached to data nodes (in GiB)."
}

variable "log_publishing_enabled" {
  type        = bool
  description = "(Optional, Default: true) Whether given log publishing option is enabled or not."
  default     = "true"
}

variable "log_type" {
  type        = string
  description = "(Required) Type of OpenSearch log. Valid values: INDEX_SLOW_LOGS, SEARCH_SLOW_LOGS, ES_APPLICATION_LOGS, AUDIT_LOGS."
  default     = "ES_APPLICATION_LOGS"
}

variable "enforce_https" {
  type        = bool
  description = "(Optional) Whether or not to require HTTPS. Defaults to true"
  default     = "true"
}

variable "tls_security_policy" {
  type        = string
  description = "(Optional) Name of the TLS security policy that needs to be applied to the HTTPS endpoint. Valid values: Policy-Min-TLS-1-0-2019-07 and Policy-Min-TLS-1-2-2019-07. Terraform will only perform drift detection if a configuration value is provided."
  default     = ""
}

variable "advanced_security_options" {
  type        = bool
  description = "(Required, Forces new resource) Whether advanced security is enabled."
  default     = true
}

variable "main_user_arn" {
  type        = string
  sensitive   = true
  description = "(Optional) ARN for the main user. Only specify if internal_user_database_enabled is not set or set to false."
  default     = null
}

variable "main_user_name" {
  type        = string
  sensitive   = true
  description = "(Optional) Main user's username, which is stored in the Amazon OpenSearch Service domain's internal database. Only specify if internal_user_database_enabled is set to true."
  default     = null
}

variable "main_user_password" {
  type        = string
  sensitive   = true
  description = "(Optional) Main user's password, which is stored in the Amazon OpenSearch Service domain's internal database. Only specify if internal_user_database_enabled is set to true."
  default     = null
}

variable "node_to_node_encryption" {
  type        = bool
  description = "(Required) Whether to enable node-to-node encryption. If the node_to_node_encryption block is not provided then this defaults to false."
  default     = "true"
}

variable "service_name" {
  type        = string
  description = "(Required) The service name. For AWS services the service name is usually in the form com.amazonaws.<region>.<service>"
  default     = "es.amazonaws.com"
}

variable "cloudwatch_log_group_name" {
  type        = string
  description = "The name of the log group. If omitted, Terraform will assign a random, unique name."
  default     = ""
}

variable "instance_type" {
  type        = string
  description = "(Optional) Instance type of data nodes in the cluster."
  default     = ""
}

variable "zone_awareness_enabled" {
  type        = bool
  description = "(Optional) Whether zone awareness is enabled, set to true for multi-az deployment."
  default     = "true"
}

variable "instance_count" {
  type        = string
  description = "(Optional) Number of instances in the cluster."
  default     = 2
}

variable "neptune_stream_poller_execution_role_arn" {
  type        = string
  description = "(Optional) IAM Role ARN of the lambda function that performs polls on neptune cluster."
  default     = ""
}

variable "ingress_cidr_blocks" {
  default     = null
  description = "List of CIDR blocks that are allowed connection to the Neptune cluster."
}

