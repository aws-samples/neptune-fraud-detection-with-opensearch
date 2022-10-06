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

output "check_for_lambda_duplicate_execution_arn" {
  value = aws_lambda_function.check_for_lambda_duplicate_execution.arn
}

output "restart_state_machine_execution_arn" {
  value = aws_lambda_function.restart_state_machine_execution.arn
}

output "stream_poller_lambda_arn" {
  value = aws_lambda_function.stream_poller_lambda.arn
}

output "stream_poller_lambda_name" {
  value = aws_lambda_function.stream_poller_lambda.function_name
}

output "neptune_stream_poller_execution_role_arn" {
  value = aws_iam_role.neptune_stream_poller_execution_role.arn
}
