# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

variable "serverless_application_name" {
  description = "application name"
  type        = string
  default     = "python-rest-tf"
}

variable "cognito_stack_name" {
  description = "an environment name for Cognito stack"
  type        = string
  default     = "serverless-api-cognito"
}

variable "environment" {
  description = "environment name"
  type        = string
  default     = "dev"
}

variable "lambda_python_runtime" {
  description = "python runtime for lambda function"
  type        = string
  default     = "python3.12"
}

variable "lambda_memory_size" {
  description = "memory size for lambda function"
  type        = number
  default     = 128
}

variable "lambda_timeout" {
  description = "timeout for lambda function"
  type        = number
  default     = 100
}
