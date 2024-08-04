provider "aws" {
  region = var.region
  default_tags {
    tags = {
      created-by : "terraform"
      project : var.project_name
    }
  }
}
