# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

variable "region" {
  description = "AWS region to deploy serverless application in"
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Unique name for this project"
  type        = string
  default     = "serverless-tf-cicd"
}

variable "create_new_role" {
  description = "Whether to create a new IAM Role. Values are true or false. Defaulted to true always."
  type        = bool
  default     = true
}

variable "codepipeline_iam_role_name" {
  description = "Name of the IAM role to be used by the Codepipeline"
  type        = string
  default     = "codepipeline-role"
}

variable "github_connection_name" {
  description = "Name of the GitHub connection to be used by the Codepipeline"
  type        = string
  default     = "github-connection-serverless"
}

variable "source_repo_name" {
  description = "Source repo name of the GitHub repository"
  type        = string
}

variable "source_repo_branch" {
  description = "Default branch in the Source repo for which CodePipeline needs to be configured"
  type        = string
  default     = "main"
}

variable "build_projects" {
  description = "Tags to be attached to the CodePipeline"
  type        = list(string)
}

variable "builder_compute_type" {
  description = "Relative path to the Apply and Destroy build spec file"
  type        = string
  default     = "BUILD_GENERAL1_SMALL"
}

variable "builder_image" {
  description = "Docker Image to be used by codebuild"
  type        = string
  default     = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
}

variable "builder_type" {
  description = "Type of codebuild run environment"
  type        = string
  default     = "LINUX_CONTAINER"
}

variable "builder_image_pull_credentials_type" {
  description = "Image pull credentials type used by codebuild project"
  type        = string
  default     = "CODEBUILD"
}

variable "build_project_source" {
  description = "aws/codebuild/standard:4.0"
  type        = string
  default     = "CODEPIPELINE"
}
