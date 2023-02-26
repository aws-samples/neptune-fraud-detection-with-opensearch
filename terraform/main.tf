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

########################################################################
# Main Terraform file containing resources & modules for the blog post #
########################################################################

locals {
  scheduler_state_machine_name = join("", [var.application_name, "Poller"])
}

data "aws_caller_identity" "current" {}

module "sample_vpc" {
  count  = var.create_sample_vpc ? 1 : 0
  source = "./modules/sample_vpc"
}

module "commons" {
  source = "./modules/commons"
}

module "neptune" {
  source                     = "./modules/neptune"
  vpc_id                     = var.create_sample_vpc ? module.sample_vpc[0].vpc_id : var.vpc_id
  subnet_ids                 = var.create_sample_vpc ? module.sample_vpc[0].private_subnets : var.subnet_ids
  port                       = var.port
  cluster_name               = var.neptune_cluster_name
  engine_version             = var.engine_version
  backup_retention_period    = var.backup_retention_period
  preferred_backup_window    = var.preferred_backup_window
  encryption_enabled         = var.encryption_enabled
  audit_logs_export_enabled  = var.audit_logs_export_enabled
  writer_identifier          = var.writer_identifier
  writer_instance_class      = var.writer_instance_class
  number_of_reader_instances = var.number_of_reader_instances
  reader_identifier_prefix   = var.reader_identifier_prefix
  reader_instance_class      = var.reader_instance_class
  ingress_cidr_blocks        = var.ingress_cidr_blocks
  open_search_sg_id          = module.aws_opensearch.opensearch_sg_id
  kms_key_arn                = module.commons.kms_key_arn
}

module "aws_opensearch" {
  source                                   = "./modules/opensearch"
  vpc_id                                   = var.create_sample_vpc ? module.sample_vpc[0].vpc_id : var.vpc_id
  subnet_ids                               = var.create_sample_vpc ? module.sample_vpc[0].private_subnets : var.subnet_ids
  domain_name                              = var.domain_name
  opensearch_version                       = var.opensearch_version
  volume_size                              = var.volume_size
  log_type                                 = var.opensearch_log_type
  tls_security_policy                      = var.tls_security_policy
  cloudwatch_log_group_name                = var.cloudwatch_log_group_name
  instance_type                            = var.opensearch_instance_type
  neptune_stream_poller_execution_role_arn = module.lambda.neptune_stream_poller_execution_role_arn
  advanced_security_options                = true
  main_user_arn                            = "arn:aws:iam::${data.aws_caller_identity.current.id}:role/${var.neptune_poller_lambda_role_name}"
  ingress_cidr_blocks                      = var.ingress_cidr_blocks
  kms_key_arn                              = module.commons.kms_key_arn
}

module "lambda" {
  source                      = "./modules/lambda"
  neptune_cluster_resource_id = module.neptune.neptune_cluster_resource_id
  neptune_reader_endpoint     = module.neptune.neptune_reader_endpoint
  neptune_port                = var.port
  opensearch_endpoint         = module.aws_opensearch.opensearch_endpoint
  opensearch_domain           = var.domain_name
  lease_dynamo_table          = module.dynamodb.lease_dynamo_table_id
  subnet_ids                  = var.create_sample_vpc ? module.sample_vpc[0].private_subnets : var.subnet_ids
  opensearch_sg_id            = module.aws_opensearch.opensearch_sg_id
  neptune_sg_id               = module.neptune.neptune_sg_id
  state_machine_name          = local.scheduler_state_machine_name
  kms_key_arn                 = module.commons.kms_key_arn
  redrive_queue_arn           = module.commons.redrive_queue_arn
}

module "scheduler_state_machine" {
  source                                   = "./modules/scheduler_state_machine"
  scheduler_state_machine_name             = local.scheduler_state_machine_name
  check_for_lambda_duplicate_execution_arn = module.lambda.check_for_lambda_duplicate_execution_arn
  restart_state_machine_execution_arn      = module.lambda.restart_state_machine_execution_arn
  stream_poller_lambda_arn                 = module.lambda.stream_poller_lambda_arn
}

module "dynamodb" {
  source                       = "./modules/dynamodb"
  vpc_id                       = var.create_sample_vpc ? module.sample_vpc[0].vpc_id : var.vpc_id
  route_table_ids              = var.create_sample_vpc ? module.sample_vpc[0].private_route_table_ids : var.route_table_ids
  create_dynamodb_vpc_endpoint = var.create_dynamodb_vpc_endpoint
  kms_key_arn                  = module.commons.kms_key_arn
}

module "monitoring" {
  source                         = "./modules/monitoring"
  create_monitoring_vpc_endpoint = var.create_monitoring_vpc_endpoint
  vpc_id                         = var.create_sample_vpc ? module.sample_vpc[0].vpc_id : var.vpc_id
  ingress_cidr_blocks            = var.ingress_cidr_blocks
  subnet_ids                     = var.create_sample_vpc ? module.sample_vpc[0].private_subnets : var.subnet_ids
  neptune_reader_endpoint        = module.neptune.neptune_reader_endpoint
  neptune_port                   = var.port
  stream_poller_lambda_name      = module.lambda.stream_poller_lambda_name
  lease_dynamo_table_id          = module.dynamodb.lease_dynamo_table_id
  scheduler_state_machine_arn    = module.scheduler_state_machine.scheduler_state_machine_arn
}

module "neptune_loader" {
  source                       = "./modules/neptune_loader"
  vpc_id                       = var.create_sample_vpc ? module.sample_vpc[0].vpc_id : var.vpc_id
  create_s3_vpc_endpoint       = true
  neptune_cluster_resource_id  = module.neptune.neptune_cluster_resource_id
  subnet_ids                   = var.create_sample_vpc ? module.sample_vpc[0].private_subnets : var.subnet_ids
  neptune_sg_id                = module.neptune.neptune_sg_id
  neptune_cluster_iam_role_arn = module.neptune.neptune_cluster_iam_role_arn
  neptune_cluster_endpoint     = module.neptune.neptune_cluster_endpoint
  neptune_port                 = var.port
  force_destroy_enabled        = true
  kms_key_arn                  = module.commons.kms_key_arn
  redrive_queue_arn            = module.commons.redrive_queue_arn
}

module "opensearch_request_lambda" {
  source              = "./modules/opensearch_request_lambda"
  opensearch_endpoint = module.aws_opensearch.opensearch_endpoint
  opensearch_sg_id    = module.aws_opensearch.opensearch_sg_id
  iam_role_arn        = module.lambda.neptune_stream_poller_execution_role_arn
  subnet_ids          = var.create_sample_vpc ? module.sample_vpc[0].private_subnets : var.subnet_ids
  kms_key_arn         = module.commons.kms_key_arn
  redrive_queue_arn   = module.commons.redrive_queue_arn
}
