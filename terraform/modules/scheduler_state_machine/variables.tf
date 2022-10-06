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

variable "application_name" {
  type        = string
  description = "(Optional) Name of the application."
  default     = "NeptuneStream"
}

variable "scheduler_state_machine_name" {
  type        = string
  description = "Name of the State Machine."
}

variable "check_for_lambda_duplicate_execution_arn" {
  type        = string
  description = "(Required) ARN of the lambda function that checks for duplicate execution."
}

variable "restart_state_machine_execution_arn" {
  description = "(Required) ARN of the lambda function that restarts the state machine."
}

variable "stream_poller_lambda_arn" {
  description = "(Required) ARN of the lambda function that polls the Neptune cluster."
}
