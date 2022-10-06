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

######################################
# Neptune Loader resources & modules #
######################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_ecr_authorization_token" "token" {}

locals {
  bucket_name = "${lower(var.application_name)}-loader-${data.aws_region.current.name}-${data.aws_caller_identity.current.id}"
}

resource "aws_vpc_endpoint" "s3" {
  count             = var.create_s3_vpc_endpoint ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"

  tags = {
    Name = "neptune-vpce-s3"
  }
}

resource "aws_s3_bucket" "neptune_s3_bucket" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy_enabled
}

resource "aws_s3_bucket_logging" "logs" {
  bucket = aws_s3_bucket.neptune_s3_bucket_logs.id

  target_bucket = aws_s3_bucket.neptune_s3_bucket.bucket
  target_prefix = "log/"
}

resource "aws_s3_bucket" "neptune_s3_bucket_logs" {
  bucket        = "${local.bucket_name}-logs"
  force_destroy = var.force_destroy_enabled
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.neptune_s3_bucket_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.neptune_s3_bucket_logs.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_versioning" "neptune_s3_bucket_versioning_logs" {
  bucket = aws_s3_bucket.neptune_s3_bucket_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sse_kms" {
  bucket = aws_s3_bucket.neptune_s3_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket_versioning" "neptune_s3_bucket_versioning" {
  bucket = aws_s3_bucket.neptune_s3_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "default" {
  count  = var.block_public_access_s3_enabled ? 1 : 0
  bucket = aws_s3_bucket.neptune_s3_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "s3_bucket_policy" {
  statement {
    sid = "AllowSSLRequestsOnly"
    actions = [
      "s3:*"
    ]
    resources = [
      "arn:aws:s3:::${aws_s3_bucket.neptune_s3_bucket.id}",
      "arn:aws:s3:::${aws_s3_bucket.neptune_s3_bucket.id}/*"
    ]
    effect = "Deny"
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"

      values = [
        "false"
      ]
    }
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
  }
}

resource "aws_s3_bucket_policy" "ssl_policy" {
  count      = var.ssl_policy_enabled ? 1 : 0
  bucket     = aws_s3_bucket.neptune_s3_bucket.id
  policy     = data.aws_iam_policy_document.s3_bucket_policy.json
  depends_on = [aws_s3_bucket_public_access_block.default]
}

resource "aws_s3_bucket_versioning" "versioning" {
  count  = var.bucket_versioning_enabled ? 1 : 0
  bucket = aws_s3_bucket.neptune_s3_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.neptune_s3_bucket.id

  queue {
    queue_arn     = aws_sqs_queue.sqs_queue.arn
    events        = ["s3:ObjectCreated:Put"]
    filter_prefix = var.nodes_folder_prefix
    filter_suffix = var.graph_load_data_format
  }

  queue {
    queue_arn     = aws_sqs_queue.sqs_queue.arn
    events        = ["s3:ObjectCreated:Put"]
    filter_prefix = var.edges_folder_prefix
    filter_suffix = var.graph_load_data_format
  }

  depends_on = [
    aws_sqs_queue_policy.sqs_queue_policy
  ]
}
