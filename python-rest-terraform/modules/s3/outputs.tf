#This solution, non-production-ready template describes AWS Codepipeline based CICD Pipeline for terraform code deployment.
#© 2023 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
#http://aws.amazon.com/agreement or other written agreement between Customer and either
#Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

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