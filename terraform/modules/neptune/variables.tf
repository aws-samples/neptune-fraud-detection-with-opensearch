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

###########################
# Neptune input variables #
###########################

variable "vpc_id" {
  type        = string
  description = "VPC id to deploy the Neptune cluster in if not creatig a sample one."
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet ids to associate the Neptune subnet group."
}

variable "cluster_name" {
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

variable "open_search_sg_id" {
  default     = null
  description = "Security group id of the OpenSearch cluster to allow it to connect to Neptune."
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN to be used with S3, Lambda, and SQS."
}
