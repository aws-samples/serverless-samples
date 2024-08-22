# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "id" {
  value       = aws_codepipeline.terraform_pipeline.id
  description = "The id of the CodePipeline"
}

output "name" {
  value       = aws_codepipeline.terraform_pipeline.name
  description = "The name of the CodePipeline"
}

output "arn" {
  value       = aws_codepipeline.terraform_pipeline.arn
  description = "The arn of the CodePipeline"
}
