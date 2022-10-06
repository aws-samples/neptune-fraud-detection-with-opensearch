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

#################
# IAM Resources #
#################

data "aws_region" "current" {}

data "aws_iam_policy_document" "state_machine_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.${data.aws_region.current.name}.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "step_function_invoke_lambda_policy_permission" {
  statement {
    sid = "AllowLambdaInvokeAction"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [
      "${var.check_for_lambda_duplicate_execution_arn}",
      "${var.restart_state_machine_execution_arn}",
      "${var.stream_poller_lambda_arn}"
    ]
    effect = "Allow"
  }
}

resource "aws_iam_role" "state_machine_execution_role" {
  name               = "NeptuneStateMachineExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.state_machine_assume_role_policy.json
}

resource "aws_iam_policy" "step_function_invoke_lambda_policy" {
  name        = "NeptuneStreamDefaultPolicy"
  path        = "/"
  description = "Allow Lambda invoke"
  policy      = data.aws_iam_policy_document.step_function_invoke_lambda_policy_permission.json
}

resource "aws_iam_policy_attachment" "step_function_invoke_lambda_policy_attachment" {
  name       = "step_function_invoke_lambda_policy_attachment"
  roles      = [aws_iam_role.state_machine_execution_role.name]
  policy_arn = aws_iam_policy.step_function_invoke_lambda_policy.arn
}

data "aws_iam_policy_document" "eventbridge_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbridge_rule_execution_role" {
  name               = "NeptuneCronExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role_policy.json
}

data "aws_iam_policy_document" "eventbridge_rule_policy_permission" {
  statement {
    sid = "AllowStateInvokeAction"
    actions = [
      "states:StartExecution"
    ]
    resources = [
      "${aws_sfn_state_machine.neptune_stream_poller.arn}"
    ]
    effect = "Allow"
  }
}

resource "aws_iam_policy" "eventbridge_rule_policy" {
  name        = "EventBridgeStartStepFunction"
  path        = "/"
  description = "Allow EventBridge State Machine invoke"
  policy      = data.aws_iam_policy_document.eventbridge_rule_policy_permission.json
}

resource "aws_iam_policy_attachment" "eventbridge_rule_policy_attachment" {
  name       = "eventbridge_rule_policy_attachment"
  roles      = [aws_iam_role.eventbridge_rule_execution_role.name]
  policy_arn = aws_iam_policy.eventbridge_rule_policy.arn
}

#################
# Step Function #
#################

resource "aws_sfn_state_machine" "neptune_stream_poller" {
  name     = var.scheduler_state_machine_name
  role_arn = aws_iam_role.state_machine_execution_role.arn
  definition = templatefile("${path.module}/files/state_machine_definition.tftpl", {
    check_for_lambda_duplicate_execution_arn = var.check_for_lambda_duplicate_execution_arn
    stream_poller_lambda_arn                 = var.stream_poller_lambda_arn
    restart_state_machine_execution_arn      = var.restart_state_machine_execution_arn
  })
}

#########################
# EventBridge resources #
#########################

resource "aws_cloudwatch_event_rule" "neptune_stream_poller_eventbridge_rule" {
  name                = join("-", [var.application_name, "PollerRule"])
  description         = "Executes the Neptune Poller Step Function Periodically"
  schedule_expression = "rate(5 minutes)"
  is_enabled          = true
}

resource "aws_cloudwatch_event_target" "neptune_stream_poller_eventbridge_target" {
  arn      = aws_sfn_state_machine.neptune_stream_poller.arn
  rule     = aws_cloudwatch_event_rule.neptune_stream_poller_eventbridge_rule.id
  role_arn = aws_iam_role.eventbridge_rule_execution_role.arn
}
