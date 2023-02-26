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

##############################
# IAM policy for AWS Neptune #
##############################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_iam_policy_document" "neptune_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["rds.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "neptune_s3_read_only_policy" {
  statement {
    actions = [
      "s3:Get*",
      "s3:List*",
      "s3-object-lambda:Get*",
      "s3-object-lambda:List*"
    ]
    resources = ["arn:aws:s3:::*"]
    effect    = "Allow"
  }

  statement {
    sid = "AllowKMSDecryptAction"
    actions = [
      "kms:Decrypt"
    ]

    resources = [
      var.kms_key_arn
    ]
    effect = "Allow"
  }
}

###############################
# Neptune resources & modules #
###############################

resource "aws_security_group" "allow_neptune_connection" {
  name        = "neptune_sg"
  description = "VPC security group ID to associate with the Neptune cluster"
  vpc_id      = var.vpc_id

  ingress {
    description = "Access to Neptune cluster"
    from_port   = var.port
    to_port     = var.port
    protocol    = "tcp"
    cidr_blocks = var.ingress_cidr_blocks
    self        = true
  }

  ingress {
    description     = "Allow access from OpenSearch security group"
    from_port       = var.port
    to_port         = var.port
    protocol        = "tcp"
    security_groups = [var.open_search_sg_id]
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
    Name = "neptune-sg"
  }
}

resource "aws_neptune_subnet_group" "default" {
  name       = "default-neptune-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "Default neptune subnet group"
  }
}

resource "aws_iam_policy" "neptune_s3_read_only_policy" {
  name        = "neptune-s3-read-only-policy"
  path        = "/"
  description = "Allowing Neptune Servuce to read data from S3"
  policy      = data.aws_iam_policy_document.neptune_s3_read_only_policy.json
}

resource "aws_iam_policy_attachment" "neptune_s3_read_only_policy_attachment" {
  name       = "neptune_s3_read_only_policy_attachment"
  roles      = [aws_iam_role.neptune_iam_role.name]
  policy_arn = aws_iam_policy.neptune_s3_read_only_policy.arn
}

resource "aws_iam_role" "neptune_iam_role" {
  name               = "NeptuneS3LoadExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.neptune_assume_role_policy.json
}

resource "aws_neptune_cluster" "cluster" {
  cluster_identifier                   = var.cluster_name
  engine_version                       = var.engine_version
  backup_retention_period              = var.backup_retention_period
  preferred_backup_window              = var.preferred_backup_window
  port                                 = var.port
  storage_encrypted                    = var.encryption_enabled
  vpc_security_group_ids               = [aws_security_group.allow_neptune_connection.id]
  enable_cloudwatch_logs_exports       = var.audit_logs_export_enabled ? ["audit"] : null
  neptune_subnet_group_name            = aws_neptune_subnet_group.default.id
  skip_final_snapshot                  = true
  iam_database_authentication_enabled  = true
  apply_immediately                    = true
  neptune_cluster_parameter_group_name = aws_neptune_cluster_parameter_group.streams.id
  iam_roles                            = [aws_iam_role.neptune_iam_role.arn]
}

resource "aws_neptune_cluster_instance" "writer" {
  cluster_identifier = aws_neptune_cluster.cluster.id
  identifier         = var.writer_identifier
  instance_class     = var.writer_instance_class
  neptune_parameter_group_name = "default.neptune1.2"
  apply_immediately  = true

  tags = {
    Name          = "writer-neptune-instance"
    InstanceType  = "writer"
    InstanceClass = var.writer_instance_class
  }
}

resource "aws_neptune_cluster_instance" "readers" {
  count              = var.number_of_reader_instances
  identifier_prefix  = var.reader_identifier_prefix
  cluster_identifier = aws_neptune_cluster.cluster.id
  instance_class     = var.reader_instance_class
  neptune_parameter_group_name = "default.neptune1.2"
  apply_immediately  = true

  tags = {
    Name          = "reader-neptune-instance"
    InstanceType  = "reader"
    InstanceClass = var.reader_instance_class
  }

  depends_on = [
    aws_neptune_cluster_instance.writer
  ]
}

resource "aws_neptune_cluster_parameter_group" "streams" {
  family      = "neptune1.2"
  name        = "stream-parameter-group"
  description = "neptune cluster parameter group"

  parameter {
    name  = "neptune_streams"
    value = 1
  }
}
