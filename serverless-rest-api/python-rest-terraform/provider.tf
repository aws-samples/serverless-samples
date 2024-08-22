# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      created-by : "terraform"
      project : var.project_name
    }
  }
}
