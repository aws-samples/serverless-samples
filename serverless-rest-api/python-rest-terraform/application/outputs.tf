# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.application_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/Prod"
}

output "api_id" {
  description = "API Gateway ID"
  value       = aws_api_gateway_rest_api.application_api.id
}

output "api_basic_usage_plan" {
  description = "API Gateway Basic Usage Plan"
  value       = aws_api_gateway_usage_plan.basic_usage_quota.id
}

output "api_enterprise_usage_plan" {
  description = "API Gateway Enterprise Usage Plan"
  value       = aws_api_gateway_usage_plan.enterprise_usage_quota.id
}

output "dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?${data.aws_region.current.name}#dashboards:name=${local.resource_name_prefix}-dashboard"
}

output "alarms_topic" {
  description = "SNS Topic ARN for Alarms"
  value       = aws_sns_topic.alarms_topic.arn
}

output "access_logs" {
  description = "CloudWatch Logs group for API Gateway access logs"
  value       = aws_cloudwatch_log_group.rest_api_access_logs.name
}

output "locations_table" {
  description = "DynamoDB table for Locations"
  value       = aws_dynamodb_table.locations_table.name
}

output "resources_table" {
  description = "DynamoDB table for Resources"
  value       = aws_dynamodb_table.resources_table.name
}

output "bookings_table" {
  description = "DynamoDB table for Bookings"
  value       = aws_dynamodb_table.bookings_table.name
}
