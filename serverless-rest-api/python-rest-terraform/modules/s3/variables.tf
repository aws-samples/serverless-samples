# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

variable "project_name" {
  description = "Name of the project to be prefixed to create the s3 bucket"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "codepipeline_role_arn" {
  description = "ARN of the codepipeline IAM role"
  type        = string
}