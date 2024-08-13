# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "arn" {
  value       = aws_s3_bucket.codepipeline_bucket.arn
  description = "The ARN of the S3 Bucket"
}

output "bucket" {
  value       = aws_s3_bucket.codepipeline_bucket.bucket
  description = "The Name of the S3 Bucket"
}

output "bucket_url" {
  value       = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.codepipeline_bucket.bucket}?region=${aws_s3_bucket.codepipeline_bucket.region}&tab=objects"
  description = "The URL of the S3 Bucket"
}

output "dynamodb_table_arn" {
  value       = aws_dynamodb_table.dynamodb_terraform_state_lock.arn
  description = "The ARN of the DynamoDB Table for Terraform state lock"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.dynamodb_terraform_state_lock.name
  description = "The Name of the DynamoDB Table for Terraform state lock"
}