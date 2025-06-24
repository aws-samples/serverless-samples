# Configure the AWS provider
provider "aws" {
  region = "us-west-1"
}

# Create an SQS queue
resource "aws_sqs_queue" "terraform_queue" {
  name                      = "terraform-example-queue"
  delay_seconds             = 90
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
  sqs_managed_sse_enabled = true

  tags = {
    Environment = "example app"
  }
}

# Create Parameter
resource "aws_ssm_parameter" "terraform-example-queue-arn" {
  name  = "terraform-example-queue-arn"
  type  = "String"
  value = aws_sqs_queue.terraform_queue.arn
}

output "terraform-example-queue-url" {
  value = aws_sqs_queue.terraform_queue.url
}
