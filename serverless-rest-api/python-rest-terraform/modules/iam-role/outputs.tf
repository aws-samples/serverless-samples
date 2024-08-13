# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "role_arn" {
  value       = var.create_new_role ? aws_iam_role.codepipeline_role[0].arn : data.aws_iam_role.existing_codepipeline_role[0].arn
  description = "The ARN of the IAM Role"
}

output "role_name" {
  value       = var.create_new_role ? aws_iam_role.codepipeline_role[0].name : data.aws_iam_role.existing_codepipeline_role[0].name
  description = "The ARN of the IAM Role"
}

output "cloudformation_role_arn" {
  value       = aws_iam_role.cloudformation_execution_role.arn
  description = "The ARN of the Cloudformation execution IAM Role"
}