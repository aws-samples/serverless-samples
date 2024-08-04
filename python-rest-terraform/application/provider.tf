provider "aws" {
  region = var.region
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
