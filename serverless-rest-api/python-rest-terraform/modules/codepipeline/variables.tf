variable "project_name" {
  description = "Unique name for this project"
  type        = string
}

variable "source_repo_name" {
  description = "Source repo name of the CodeCommit repository"
  type        = string
}

variable "source_repo_branch" {
  description = "Default branch in the Source repo for which CodePipeline needs to be configured"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name to be used for storing the artifacts"
  type        = string
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name to perform the terraform state lock"
  type        = string
}

variable "codepipeline_role_arn" {
  description = "ARN of the codepipeline IAM role"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "codestar_connection_arn" {
  description = "ARN of the CodeStar connection"
  type        = string
}

variable "cloudformation_role_arn" {
  description = "ARN of the CloudFormation execution role"
  type        = string
}