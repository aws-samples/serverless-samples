# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

data "aws_region" "current" {}

locals {
  pipeline_variables = [
    {
      name          = "s3_bucket"
      default_value = var.s3_bucket_name
    },
    {
      name          = "dynamodb_table"
      default_value = var.dynamodb_table_name
    },
    {
      name          = "app_name"
      default_value = "my-app"
    },
    {
      name          = "cognito_stack_name"
      default_value = "${var.project_name}-Cognito-Testing"
    },
    {
      name          = "region"
      default_value = data.aws_region.current.id
    }
  ]
  stage_variables = [
    {
      "name" : "tf_state_bucket",
      "value" : "#{variables.s3_bucket}"
    },
    {
      "name" : "tf_state_table",
      "value" : "#{variables.dynamodb_table}"
    },
    {
      "name" : "TF_VAR_serverless_application_name",
      "value" : "#{variables.app_name}"
    },
    {
      "name" : "TF_VAR_cognito_stack_name",
      "value" : "#{variables.cognito_stack_name}"
    },
    {
      "name" : "TF_VAR_region",
      "value" : "#{variables.region}"
    }
  ]
}
resource "aws_codepipeline" "terraform_pipeline" {

  name          = "${var.project_name}-pipeline"
  role_arn      = var.codepipeline_role_arn
  pipeline_type = "V2"

  artifact_store {
    location = var.s3_bucket_name
    type     = "S3"
    encryption_key {
      id   = var.kms_key_arn
      type = "KMS"
    }
  }

  dynamic "variable" {
    for_each = local.pipeline_variables
    content {
      name          = variable.value.name
      default_value = variable.value.default_value
    }
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeStarSourceConnection"
      namespace        = "SourceVariables"
      output_artifacts = ["SourceOutput"]
      run_order        = 1

      configuration = {
        ConnectionArn    = var.codestar_connection_arn
        FullRepositoryId = var.source_repo_name
        BranchName       = var.source_repo_branch
      }
    }
  }

  stage {
    name = "Application-Test"

    action {
      name             = "Validate-Application"
      category         = "Test"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["SourceOutput"]
      output_artifacts = ["ValidateOutput"]
      run_order        = 2

      configuration = {
        ProjectName = "${var.project_name}-validate"
      }
    }

  }

  stage {
    name = "Cognito-Setup"

    action {
      name            = "Create-Cognito-ChangeSet"
      category        = "Deploy"
      owner           = "AWS"
      version         = "1"
      provider        = "CloudFormation"
      input_artifacts = ["ValidateOutput"]
      run_order       = 3

      configuration = {
        ActionMode    = "CHANGE_SET_REPLACE",
        RoleArn       = var.cloudformation_role_arn,
        StackName     = "${var.project_name}-Cognito-Testing",
        ChangeSetName = "${var.project_name}-ChangeSet-Cognito-Testing",
        TemplatePath  = "ValidateOutput::shared/cognito.yaml",
        Capabilities  = "CAPABILITY_IAM"
      }
    }
    action {
      name             = "Execute-Cognito-ChangeSet"
      category         = "Deploy"
      owner            = "AWS"
      version          = "1"
      provider         = "CloudFormation"
      input_artifacts  = ["ValidateOutput"]
      output_artifacts = ["${var.project_name}CognitoTestingChangeSet"]
      run_order        = 4

      configuration = {
        ActionMode    = "CHANGE_SET_EXECUTE",
        RoleArn       = var.cloudformation_role_arn,
        StackName     = "${var.project_name}-Cognito-Testing",
        ChangeSetName = "${var.project_name}-ChangeSet-Cognito-Testing",
        TemplatePath  = "ValidateOutput::cognito.yaml",
        Capabilities  = "CAPABILITY_IAM"
      }
    }
  }

  stage {
    name = "Application-Deploy"

    action {
      name             = "Plan-Application-Test"
      category         = "Test"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["ValidateOutput"]
      output_artifacts = ["TestPlanOutput"]
      run_order        = 5

      configuration = {
        ProjectName = "${var.project_name}-plan"
        EnvironmentVariables : jsonencode(concat(local.stage_variables, [{
          "name" : "TF_VAR_environment",
          "value" : "Test"
        }]))
      }
    }
    action {
      name             = "Plan-Application-Prod"
      category         = "Test"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["ValidateOutput"]
      output_artifacts = ["ProdPlanOutput"]
      run_order        = 5

      configuration = {
        ProjectName = "${var.project_name}-plan"
        EnvironmentVariables : jsonencode(concat(local.stage_variables, [{
          "name" : "TF_VAR_environment",
          "value" : "Prod"
        }]))
      }
    }

    action {
      name             = "Apply-Application-Test"
      category         = "Build"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["TestPlanOutput"]
      output_artifacts = ["TestApplyOutput"]
      run_order        = 6

      configuration = {
        ProjectName = "${var.project_name}-apply"
        EnvironmentVariables : jsonencode(concat(local.stage_variables, [{
          "name" : "TF_VAR_environment",
          "value" : "Test"
        }]))
      }
    }
    action {
      name             = "Integration-Application-Test"
      category         = "Build"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["TestApplyOutput"]
      output_artifacts = ["TestIntegrationOutput"]
      run_order        = 7

      configuration = {
        ProjectName = "${var.project_name}-test"
        EnvironmentVariables : jsonencode(concat(local.stage_variables, [{
          "name" : "TF_VAR_environment",
          "value" : "Test"
        }]))
      }
    }
    action {
      name      = "Apply-Application-Prod-Approval"
      category  = "Approval"
      owner     = "AWS"
      version   = "1"
      provider  = "Manual"
      run_order = 8
    }
    action {
      name             = "Apply-Application-Prod"
      category         = "Build"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["ProdPlanOutput"]
      output_artifacts = ["ProdApplyOutput"]
      run_order        = 9

      configuration = {
        ProjectName = "${var.project_name}-apply"
        EnvironmentVariables : jsonencode(concat(local.stage_variables, [{
          "name" : "TF_VAR_environment",
          "value" : "Prod"
        }]))
      }
    }
    action {
      name             = "Integration-Application-Prod"
      category         = "Build"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["ProdApplyOutput"]
      output_artifacts = ["ProdIntegrationOutput"]
      run_order        = 10

      configuration = {
        ProjectName = "${var.project_name}-test"
        EnvironmentVariables : jsonencode(concat(local.stage_variables, [{
          "name" : "TF_VAR_environment",
          "value" : "Prod"
        }]))
      }
    }
  }

  stage {
    name = "Destroy"

    action {
      name      = "Destroy-Approval"
      category  = "Approval"
      owner     = "AWS"
      version   = "1"
      provider  = "Manual"
      run_order = 11
    }
    action {
      name             = "Destroy-Application-Test"
      category         = "Build"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["TestApplyOutput"]
      output_artifacts = ["TestDestroyOutput"]
      run_order        = 12

      configuration = {
        ProjectName = "${var.project_name}-destroy"
        EnvironmentVariables : jsonencode(concat(local.stage_variables, [{
          "name" : "TF_VAR_environment",
          "value" : "Test"
        }]))
      }
    }
    action {
      name             = "Destroy-Application-Prod"
      category         = "Build"
      owner            = "AWS"
      version          = "1"
      provider         = "CodeBuild"
      input_artifacts  = ["ProdApplyOutput"]
      output_artifacts = ["ProdDestroyOutput"]
      run_order        = 12

      configuration = {
        ProjectName = "${var.project_name}-destroy"
        EnvironmentVariables : jsonencode(concat(local.stage_variables, [{
          "name" : "TF_VAR_environment",
          "value" : "Prod"
        }]))
      }
    }
    action {
      name      = "Destroy-Cognito-ChangeSet"
      category  = "Deploy"
      owner     = "AWS"
      version   = "1"
      provider  = "CloudFormation"
      run_order = 13

      configuration = {
        ActionMode = "DELETE_ONLY",
        RoleArn    = var.cloudformation_role_arn,
        StackName  = "${var.project_name}-Cognito-Testing",
      }
    }
  }
}
