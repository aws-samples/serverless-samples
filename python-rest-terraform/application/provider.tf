# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

provider "aws" {
  default_tags {
    tags = {
      created-by : "terraform"
      project : var.serverless_application_name
      environment : var.environment
    }
  }
}

terraform {
  backend "s3" {}
}
