# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

project_name       = "serverless-tf-cicd"
source_repo_name   = "<github-repo-owner>/serverless-app-demo-aws" #Change the Owner as per your Github Username
region             = "eu-west-2"
source_repo_branch = "main"
create_new_role    = true
# codepipeline_iam_role_name = <Role name> - Use this to specify the role name to be used by codepipeline if the create_new_role flag is set to false.
build_projects = ["validate", "plan", "apply", "test", "destroy"]
