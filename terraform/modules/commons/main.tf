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

########################################
# AWS Key Management Service resources #
########################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_kms_key" "kms_key" {
  description             = "KMS key for encryption of resources."
  deletion_window_in_days = 10
  policy                  = data.aws_iam_policy_document.kms_policy.json
  enable_key_rotation     = true
}

data "aws_iam_policy_document" "kms_policy" {
  statement {
    sid = "Allow administration of the key"

    actions = [
      "kms:*"
    ]

    resources = [
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.id}:key/*"
    ]

    principals {
      type = "AWS"
      identifiers = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      ]
    }
  }

  statement {
    sid = "Allow S3 access"

    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]

    resources = [
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.id}:key/*"
    ]

    principals {
      type = "Service"
      identifiers = [
        "s3.amazonaws.com"
      ]
    }
  }

  statement {
    sid = "Allow Lambda access"

    actions = [
      "kms:Decrypt"
    ]

    resources = [
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.id}:key/*"
    ]

    principals {
      type = "Service"
      identifiers = [
        "lambda.amazonaws.com"
      ]
    }
  }

  statement {
    sid = "Allow DynamoDB access"

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:CreateGrant",
      "kms:ListGrants",
      "kms:DescribeKey"
    ]

    resources = [
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.id}:key/*"
    ]

    principals {
      type = "Service"
      identifiers = [
        "dynamodb.amazonaws.com"
      ]
    }
  }

  statement {
    sid = "Allow CloudWatch logs"

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*"
    ]

    resources = [
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.id}:key/*"
    ]

    principals {
      type = "Service"
      identifiers = [
        "logs.${data.aws_region.current.name}.amazonaws.com"
      ]
    }

    condition {
      test     = "ArnEquals"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values = [
        "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.id}:log-group:*"
      ]
    }
  }
}

resource "aws_kms_alias" "kms_key_alias" {
  name          = var.kms_alias == null ? "alias/neptune-loader-s3-encryption-key" : var.kms_alias
  target_key_id = aws_kms_key.kms_key.key_id
}

#####################
# AWS SQS resources #
#####################

resource "aws_sqs_queue" "sqs_queue" {
  name                       = "${var.application_name}-redrive-queue"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  sqs_managed_sse_enabled    = true
}

resource "aws_sqs_queue_policy" "sqs_queue_policy" {
  queue_url = aws_sqs_queue.sqs_queue.id
  policy    = data.aws_iam_policy_document.sqs_policy.json
}

data "aws_iam_policy_document" "sqs_policy" {
  source_policy_documents = [
    data.aws_iam_policy_document.allow_principal.json,
    data.aws_iam_policy_document.allow_lambda.json
  ]
}

data "aws_iam_policy_document" "allow_principal" {
  statement {
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:GetQueueAttributes",
      "sqs:DeleteMessage"
    ]

    principals {
      type        = "AWS"
      identifiers = [data.aws_caller_identity.current.account_id]
    }

    resources = [
      aws_sqs_queue.sqs_queue.arn
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["true"]
    }
  }
}

data "aws_iam_policy_document" "allow_lambda" {
  statement {
    actions = [
      "sqs:SendMessage",
    ]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    resources = [
      aws_sqs_queue.sqs_queue.arn
    ]

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.id}:function:*"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["true"]
    }
  }
}
