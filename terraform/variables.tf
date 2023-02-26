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

########################
# Main Input variables #
########################

variable "region" {
  default     = "us-west-2"
  description = "AWS region"
}

variable "application_name" {
  type        = string
  description = "(Optional) Name of the application."
  default     = "NeptuneStream"
}

variable "environment" {
  type        = string
  description = "Name of the environment (ie dev, test, prod)."
  default     = "dev"
}

variable "create_sample_vpc" {
  type        = bool
  default     = true
  description = "Sample VPC to deploy the Neptune cluster in if not importing one."
}

variable "vpc_id" {
  default     = null
  description = "VPC id to deploy the Neptune cluster in if not creatig a sample one."
}

variable "subnet_ids" {
  default     = null
  description = "List of subnet ids to associate the Neptune subnet group."
}

variable "route_table_ids" {
  default     = null
  description = "List of route tables to associate the DynamoDB VPC endpoint."
}

##################################
# Neptune module input variables # 
##################################

variable "neptune_cluster_name" {
  type        = string
  default     = "neptune-cluster-demo"
  description = "Name for the Neptune cluster. If not provided Terraform will assign a random, unique identifier."
}

variable "encryption_enabled" {
  type        = bool
  default     = true
  description = "A boolean flag to enable/disable Neptune cluster encryption."
}

variable "backup_retention_period" {
  default     = 7
  description = "Number of days to retain backups for."
}

variable "engine_version" {
  default     = "1.2.0.2"
  description = "Version number of the database engine."
}

variable "preferred_backup_window" {
  default     = "07:00-09:00"
  description = "The daily time range during which automated backups are created. Time in UTC."
}

variable "port" {
  default     = 8182
  description = "The port on which the Neptune database accepts connections."
}

variable "ingress_cidr_blocks" {
  default     = null
  description = "List of CIDR blocks that are allowed connection to the Neptune cluster."
}

#####################################
# OpenSearch module input variables #
#####################################

variable "reader_instance_class" {
  default     = "db.t3.medium"
  description = "The instance class to use for readers."
}

variable "reader_identifier_prefix" {
  default     = "demo-reader-instance"
  description = "Prefix for reader instances identifier."
}

variable "writer_identifier" {
  default     = "demo-writer-instance"
  description = "Identifier for the writer instance."
}

variable "number_of_reader_instances" {
  default     = 1
  description = "The instance class to use for readers."
}

variable "writer_instance_class" {
  default     = "db.t3.medium"
  description = "The instance class to use for the writer instance."
}

variable "audit_logs_export_enabled" {
  default     = true
  description = "A boolean flag to enable/disable audit logging."
}

variable "domain_name" {
  type        = string
  description = "(Required) Name of the domain."
  default     = "demo-opensearch-domain"
}

variable "opensearch_instance_type" {
  type        = string
  description = "(Optional) Instance type of data nodes in the cluster."
  default     = "t3.small.search"
}

variable "opensearch_version" {
  type        = string
  description = "(Optional) Version of OpenSearch to deploy. Defaults to 1.2"
  default     = "OpenSearch_1.2"
}

variable "volume_size" {
  type        = number
  description = "(Required if ebs_enabled is set to true.) Size of EBS volumes attached to data nodes (in GiB)."
  default     = 10
}

variable "opensearch_log_type" {
  type        = string
  description = "(Required) Type of OpenSearch log. Valid values: INDEX_SLOW_LOGS, SEARCH_SLOW_LOGS, ES_APPLICATION_LOGS, AUDIT_LOGS."
  default     = "AUDIT_LOGS"
}

variable "tls_security_policy" {
  type        = string
  description = "(Optional) Name of the TLS security policy that needs to be applied to the HTTPS endpoint. Valid values: Policy-Min-TLS-1-0-2019-07 and Policy-Min-TLS-1-2-2019-07. Terraform will only perform drift detection if a configuration value is provided."
  default     = "Policy-Min-TLS-1-2-2019-07"
}

variable "cloudwatch_log_group_name" {
  type        = string
  description = "The name of the log group. If omitted, Terraform will assign a random, unique name."
  default     = "/aws/opensearch/demo-opensearch"
}

variable "main_user_arn" {
  type        = string
  sensitive   = true
  description = "(Optional) ARN for the main user. Only specify if internal_user_database_enabled is not set or set to false."
  default     = null
}

variable "neptune_poller_lambda_role_name" {
  type        = string
  description = "(Optional) IAM Role of the lambda function that performs polls on neptune cluster."
  default     = "NeptuneStreamPollerExecutionRole"
}

variable "create_dynamodb_vpc_endpoint" {
  type        = bool
  description = "A Boolean value that defaults to true. You only need to change it to false if you have already created a DynamoDB endpoint in your VPC."
  default     = true
}
variable "create_monitoring_vpc_endpoint" {
  type        = bool
  description = "A Boolean value that defaults to true. You only need to change it to false if you have already created a monitoring endpoint in your VPC."
  default     = true
}
