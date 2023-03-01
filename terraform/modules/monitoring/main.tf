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

########################
# Monitoring Resources #
########################

data "aws_region" "current" {}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

resource "aws_security_group" "monitoring_sg" {
  count       = var.create_monitoring_vpc_endpoint ? 1 : 0
  name        = "monitoring_sg"
  description = "VPC security group to allow traffic for monitoring VPC endpoint"
  vpc_id      = var.vpc_id

  ingress {
    description = "Enable HTTPS Access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.selected.cidr_block]
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
    Name = "monitoring-sg"
  }
}

resource "aws_vpc_endpoint" "monitoring" {
  count              = var.create_monitoring_vpc_endpoint ? 1 : 0
  vpc_id             = var.vpc_id
  service_name       = "com.amazonaws.${data.aws_region.current.name}.monitoring"
  vpc_endpoint_type  = "Interface"
  security_group_ids = [aws_security_group.monitoring_sg[0].id]
  subnet_ids         = var.subnet_ids
}

resource "aws_vpc_endpoint" "vpc_dynamodb_endpoint" {
  vpc_id       = var.vpc_id
  service_name = "com.amazonaws.${data.aws_region.current.name}.dynamodb"
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.application_name}-neptune-stream-dashboard"

  dashboard_body = templatefile("${path.module}/files/neptune_stream_dashboard.tftpl",
    {
      application_name            = var.application_name
      neptune_reader_endpoint     = var.neptune_reader_endpoint
      neptune_port                = var.neptune_port
      region                      = data.aws_region.current.name
      stream_poller_lambda_name   = var.stream_poller_lambda_name
      lease_dynamo_table_id       = var.lease_dynamo_table_id
      scheduler_state_machine_arn = var.scheduler_state_machine_arn
    }
  )
}
