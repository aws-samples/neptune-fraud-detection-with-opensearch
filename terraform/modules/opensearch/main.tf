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

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

resource "aws_opensearch_domain" "opensearch_cluster" {
  depends_on = [
    aws_iam_service_linked_role.opensearch,
    aws_cloudwatch_log_group.opensearch_log,
    aws_cloudwatch_log_resource_policy.opensearch_log_publishing_policy
  ]

  domain_name    = var.domain_name
  engine_version = var.opensearch_version

  cluster_config {
    instance_type          = var.instance_type
    instance_count         = var.instance_count
    zone_awareness_enabled = var.zone_awareness_enabled
  }

  vpc_options {
    subnet_ids         = [var.subnet_ids[0], var.subnet_ids[1]]
    security_group_ids = [aws_security_group.opensearch_sg.id]
  }

  encrypt_at_rest {
    enabled    = var.encrypt_at_rest
    kms_key_id = var.kms_key_arn
  }

  ebs_options {
    ebs_enabled = var.ebs_enabled
    volume_size = var.volume_size
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_log.arn
    enabled                  = var.log_publishing_enabled
    log_type                 = var.log_type
  }

  domain_endpoint_options {
    enforce_https       = var.enforce_https
    tls_security_policy = var.tls_security_policy
  }

  advanced_security_options {
    enabled = var.advanced_security_options
    master_user_options {
      master_user_arn = var.main_user_arn
    }
  }

  node_to_node_encryption {
    enabled = var.node_to_node_encryption
  }

  tags = {
    InstanceClass = var.instance_type
    Version       = var.opensearch_version
  }
}

resource "aws_iam_service_linked_role" "opensearch" {
  aws_service_name = var.service_name
  description      = "Service Linked Role for Amazon OpenSearch"
}

resource "aws_cloudwatch_log_group" "opensearch_log" {
  name              = var.cloudwatch_log_group_name
  retention_in_days = 30
  kms_key_id        = var.kms_key_arn
}

data "aws_iam_policy_document" "opensearch_log_publishing_policy" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:PutLogEventsBatch",
    ]

    resources = ["arn:aws:logs:*"]

    principals {
      identifiers = ["es.amazonaws.com"]
      type        = "Service"
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "opensearch_log_publishing_policy" {
  policy_document = data.aws_iam_policy_document.opensearch_log_publishing_policy.json
  policy_name     = "opensearch_log_publishing_policy"
}

resource "aws_security_group" "opensearch_sg" {
  name        = "opensearch-sg"
  description = "OpenSearch security group"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow ingress on port 443 for the Neptune VPC CIDR block"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"

    cidr_blocks = [
      data.aws_vpc.selected.cidr_block
    ]
  }

  ingress {
    description = "Allow access to opensearch cluster on port 443 to specified CIDR blocks."
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"

    cidr_blocks = var.ingress_cidr_blocks
  }

  egress {
    description      = "Enable outbound traffic"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "opensearch-sg"
  }
}

resource "aws_opensearch_domain_policy" "main" {
  domain_name = aws_opensearch_domain.opensearch_cluster.domain_name

  access_policies = <<POLICIES
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": {
        "AWS": "*"
      },
      "Action": "es:*",
      "Resource": "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.id}:domain/${var.domain_name}/*",
      "Condition": {
        "StringNotLike": {
          "aws:PrincipalArn": "${var.neptune_stream_poller_execution_role_arn}"
        }
      }
    }
  ]
}
POLICIES
}
