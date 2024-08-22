# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

locals {
  account_id           = data.aws_caller_identity.current.account_id
  region               = data.aws_region.current.name
  lambda_functions_set = toset(["locations", "bookings", "resources", "authorizer"])
  resource_name_prefix = "${var.serverless_application_name}-${random_pet.this.id}"
  dynamodb_details = tomap({
    "locations" = {
      "name"                           = "${local.resource_name_prefix}-locations-table"
      "alarm_read_capacity_threshold"  = 1
      "alarm_write_capacity_threshold" = 1
    },
    "bookings" = {
      "name"                           = "${local.resource_name_prefix}-bookings-table"
      "alarm_read_capacity_threshold"  = 1
      "alarm_write_capacity_threshold" = 1
    },
    "resources" = {
      "name"                           = "${local.resource_name_prefix}-resources-table"
      "alarm_read_capacity_threshold"  = 1
      "alarm_write_capacity_threshold" = 1
    },
  })
}

resource "random_pet" "this" {
  length = 2
}

# Lambda IAM Permissions
resource "aws_iam_role" "lambda_role" {
  name               = "${local.resource_name_prefix}-lambda-permissions"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}
resource "aws_iam_policy" "lambda_role_policy" {
  name        = "${local.resource_name_prefix}-lambda-policy"
  description = "${local.resource_name_prefix}-lambda-policy"
  policy      = data.aws_iam_policy_document.lambda_role_policy_document.json
}
resource "aws_iam_role_policy_attachment" "locations_attach1" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_role_policy.arn
}
resource "aws_iam_role_policy_attachment" "locations_attach2" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess"
}
resource "aws_iam_role_policy_attachment" "locations_attach3" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


resource "aws_iam_role" "authorizer_function_execution_role" {
  name               = "${local.resource_name_prefix}-authorizer-permissions"
  assume_role_policy = data.aws_iam_policy_document.api_assume_role.json
}
resource "aws_iam_policy" "lambda_authorizer_role_policy" {
  name        = "${local.resource_name_prefix}-authorizer-policy"
  description = "${local.resource_name_prefix}-authorizer-policy"
  policy      = data.aws_iam_policy_document.lambda_authorizer_role_policy_document.json
}
resource "aws_iam_role_policy_attachment" "authorizer_attach1" {
  role       = aws_iam_role.authorizer_function_execution_role.name
  policy_arn = aws_iam_policy.lambda_authorizer_role_policy.arn
}


resource "aws_iam_role" "api_logging_role" {
  name               = "${local.resource_name_prefix}-api-logging-permissions"
  assume_role_policy = data.aws_iam_policy_document.api_assume_role.json
}
resource "aws_iam_role_policy_attachment" "api_logging_attach" {
  role       = aws_iam_role.api_logging_role.name
  policy_arn = data.aws_iam_policy.api_cloudwatch_logging.arn
}

# Lambda Functions supporting resources

module "s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "3.15.2"

  bucket_prefix = "${local.resource_name_prefix}-"
  force_destroy = true

  # S3 bucket-level Public Access Block configuration
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  versioning = {
    enabled = true
  }
}

module "lambda_layer_s3" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.1"

  create_layer = true

  layer_name          = "${local.resource_name_prefix}-layer"
  description         = "Lambda layer with all dependencies"
  compatible_runtimes = [var.lambda_python_runtime]
  runtime             = var.lambda_python_runtime # required to force layers to do pip install

  source_path = [
    {
      path             = "${path.module}/src/lambda_layer"
      pip_requirements = true
      prefix_in_zip    = "python" # required to get the path correct
    }
  ]

  store_on_s3 = true
  s3_bucket   = module.s3_bucket.s3_bucket_id
}

# Lambda Functions

module "lambda_functions" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "7.7.1"

  for_each = local.lambda_functions_set

  function_name = "${local.resource_name_prefix}-${each.key}-lambda-function"
  description   = "${each.key}-lambda-function"
  handler       = "${each.key}.lambda_handler"
  runtime       = var.lambda_python_runtime
  architectures = ["x86_64"]
  publish       = true
  timeout       = 100
  create_role   = false
  lambda_role   = aws_iam_role.lambda_role.arn
  tracing_mode  = "Active"

  source_path = "${path.module}/src/api/"

  store_on_s3 = true
  s3_bucket   = module.s3_bucket.s3_bucket_id
  s3_prefix   = "lambda-builds/"

  artifacts_dir = "${path.root}/builds/package_dir/"

  layers = [
    module.lambda_layer_s3.lambda_layer_arn,
  ]

  environment_variables = {
    LOCATIONS_TABLE          = aws_dynamodb_table.locations_table.name
    RESOURCES_TABLE          = aws_dynamodb_table.resources_table.name
    BOOKINGS_TABLE           = aws_dynamodb_table.bookings_table.name
    AWS_EMF_NAMESPACE        = var.serverless_application_name
    AWS_XRAY_TRACING_NAME    = var.serverless_application_name
    AWS_XRAY_CONTEXT_MISSING = "LOG_ERROR"
    USER_POOL_ID             = data.aws_cloudformation_stack.cognito_stack.outputs["UserPool"]
    APPLICATION_CLIENT_ID    = data.aws_cloudformation_stack.cognito_stack.outputs["UserPoolClient"]
    ADMIN_GROUP_NAME         = data.aws_cloudformation_stack.cognito_stack.outputs["UserPoolAdminGroupName"]
  }

  logging_log_group                 = "${local.resource_name_prefix}/lambda/${each.key}"
  cloudwatch_logs_retention_in_days = 7

  allowed_triggers = {
    APIGatewayAny = {
      service    = "apigateway"
      source_arn = "arn:aws:execute-api:${local.region}:${local.account_id}:${aws_api_gateway_rest_api.application_api.id}/*/*/*"
    }
  }
  create_sam_metadata = true
}


resource "aws_dynamodb_table" "locations_table" {
  name           = local.dynamodb_details["locations"]["name"]
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "locationid"

  attribute {
    name = "locationid"
    type = "S"
  }
  point_in_time_recovery {
    enabled = true
  }
}


resource "aws_dynamodb_table" "resources_table" {
  name           = local.dynamodb_details["resources"]["name"]
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "resourceid"

  attribute {
    name = "resourceid"
    type = "S"
  }
  attribute {
    name = "locationid"
    type = "S"
  }
  global_secondary_index {
    name            = "locationidGSI"
    hash_key        = "locationid"
    write_capacity  = 2
    read_capacity   = 2
    projection_type = "ALL"
  }
  point_in_time_recovery {
    enabled = true
  }
}


resource "aws_dynamodb_table" "bookings_table" {
  name           = local.dynamodb_details["bookings"]["name"]
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "bookingid"

  attribute {
    name = "bookingid"
    type = "S"
  }
  attribute {
    name = "userid"
    type = "S"
  }
  attribute {
    name = "resourceid"
    type = "S"
  }
  attribute {
    name = "starttimeepochtime"
    type = "N"
  }
  global_secondary_index {
    name            = "useridGSI"
    hash_key        = "userid"
    write_capacity  = 2
    read_capacity   = 2
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "bookingsByUserByTimeGSI"
    hash_key        = "userid"
    range_key       = "starttimeepochtime"
    write_capacity  = 2
    read_capacity   = 2
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "bookingsByResourceByTimeGSI"
    hash_key        = "resourceid"
    range_key       = "starttimeepochtime"
    write_capacity  = 2
    read_capacity   = 2
    projection_type = "ALL"
  }
  point_in_time_recovery {
    enabled = true
  }
}


# API Gateway configurations
resource "aws_cloudwatch_log_group" "rest_api_access_logs" {
  name              = "${local.resource_name_prefix}/api/${aws_api_gateway_rest_api.application_api.id}"
  retention_in_days = 7
  kms_key_id        = aws_kms_key.sns_key.arn
}

resource "aws_api_gateway_rest_api" "application_api" {
  body = templatefile("${path.module}/src/api/openapi.tftpl", {
    AwsRegion            = local.region,
    LocationsFunction    = module.lambda_functions["locations"].lambda_function_arn,
    ResourcesFunction    = module.lambda_functions["resources"].lambda_function_arn,
    BookingsFunction     = module.lambda_functions["bookings"].lambda_function_arn,
    AuthorizerFunction   = module.lambda_functions["authorizer"].lambda_function_arn,
    AuthorizerLambdaRole = aws_iam_role.authorizer_function_execution_role.arn
  })
  name             = "${local.resource_name_prefix}-api"
  fail_on_warnings = true

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_deployment" "application_api" {
  rest_api_id = aws_api_gateway_rest_api.application_api.id

  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api.application_api.body))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "application_api" {
  for_each = toset(["Prod", "Stage"])

  deployment_id        = aws_api_gateway_deployment.application_api.id
  rest_api_id          = aws_api_gateway_rest_api.application_api.id
  stage_name           = each.key
  xray_tracing_enabled = true
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.rest_api_access_logs.arn
    format          = jsonencode({ "requestId" : "$context.requestId", "ip" : "$context.identity.sourceIp", "requestTime" : "$context.requestTime", "httpMethod" : "$context.httpMethod", "routeKey" : "$context.routeKey", "status" : "$context.status", "protocol" : "$context.protocol", "integrationStatus" : "$context.integrationStatus", "integrationLatency" : "$context.integrationLatency", "responseLength" : "$context.responseLength" })
  }
}

resource "aws_api_gateway_usage_plan" "basic_usage_quota" {
  name        = "${local.resource_name_prefix}-BasicUsagePlan"
  description = "API Gateway BasicUsagePlan for ${local.resource_name_prefix}"

  api_stages {
    api_id = aws_api_gateway_rest_api.application_api.id
    stage  = aws_api_gateway_stage.application_api["Stage"].stage_name
  }

  quota_settings {
    limit  = 100
    period = "DAY"
  }

  throttle_settings {
    burst_limit = 10
    rate_limit  = 5
  }
}


resource "aws_api_gateway_usage_plan" "enterprise_usage_quota" {
  name        = "${local.resource_name_prefix}-EnterpriseUsagePlan"
  description = "API Gateway EnterpriseUsagePlan for ${local.resource_name_prefix}"

  api_stages {
    api_id = aws_api_gateway_rest_api.application_api.id
    stage  = aws_api_gateway_stage.application_api["Prod"].stage_name
  }

  quota_settings {
    limit  = 10000
    period = "DAY"
  }

  throttle_settings {
    burst_limit = 1000
    rate_limit  = 500
  }
}

resource "aws_api_gateway_account" "demo" {
  cloudwatch_role_arn = aws_iam_role.api_logging_role.arn
}

# Alert and Notifications
resource "aws_kms_key" "sns_key" {
  description              = "CMK for SNS alarms topic"
  enable_key_rotation      = true
  deletion_window_in_days  = 20
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  key_usage                = "ENCRYPT_DECRYPT"

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "key-default-1"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.account_id}:root"
        },
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow usage of the key"
        Effect = "Allow"
        Principal = {
          Service = ["logs.${local.region}.amazonaws.com", "sns.amazonaws.com"]
        },
        Action = [
          "kms:Encrypt*",
          "kms:Decrypt*",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:Describe*"
        ],
        Resource = "*"
      },
    ]
  })
}

resource "aws_sns_topic" "alarms_topic" {
  name              = "${local.resource_name_prefix}-alarms-topic"
  kms_master_key_id = aws_kms_key.sns_key.arn
}

resource "aws_cloudwatch_metric_alarm" "api_alarms" {
  alarm_name          = "${local.resource_name_prefix}-api-5XXError"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "API Gateway 5XXError alarm"
  alarm_actions       = [aws_sns_topic.alarms_topic.arn]
  dimensions = {
    ApiName = "${local.resource_name_prefix}-api"
  }
}

resource "aws_cloudwatch_metric_alarm" "function_alarms_errors" {
  for_each = local.lambda_functions_set

  alarm_name          = "${local.resource_name_prefix}-${each.key}-lambda-function-Errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "${each.key} lambda function Errors alarm"
  alarm_actions       = [aws_sns_topic.alarms_topic.arn]
  dimensions = {
    FunctionName = module.lambda_functions["${each.key}"].lambda_function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "function_alarms_throttles" {
  for_each = local.lambda_functions_set

  alarm_name          = "${local.resource_name_prefix}-${each.key}-lambda-function-Throttles"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "${each.key} lambda function Errors alarm"
  alarm_actions       = [aws_sns_topic.alarms_topic.arn]
  dimensions = {
    FunctionName = module.lambda_functions["${each.key}"].lambda_function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_read_alarms" {
  for_each = local.dynamodb_details

  alarm_name          = "${local.resource_name_prefix}-dynamodb-ReadThrottleEvents-${each.key}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = each.value["alarm_read_capacity_threshold"]
  alarm_description   = "DynamoDB ReadThrottleEvents alarm"
  alarm_actions       = [aws_sns_topic.alarms_topic.arn]
  dimensions = {
    TableName = each.value["name"]
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_write_alarms" {
  for_each = local.dynamodb_details

  alarm_name          = "${local.resource_name_prefix}-dynamodb-WriteThrottleEvents-${each.key}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = each.value["alarm_write_capacity_threshold"]
  alarm_description   = "DynamoDB WriteThrottleEvents alarm"
  alarm_actions       = [aws_sns_topic.alarms_topic.arn]
  dimensions = {
    TableName = each.value["name"]
  }
}

resource "aws_cloudwatch_dashboard" "dashbaord" {
  dashboard_name = "${local.resource_name_prefix}-dashboard"
  dashboard_body = templatefile("${path.module}/dashboard.tftpl", {
    AwsRegion          = local.region,
    LocationsFunction  = module.lambda_functions["locations"].lambda_function_name,
    ResourcesFunction  = module.lambda_functions["resources"].lambda_function_name,
    BookingsFunction   = module.lambda_functions["bookings"].lambda_function_name,
    AuthorizerFunction = module.lambda_functions["authorizer"].lambda_function_name,
    LocationsTable     = aws_dynamodb_table.locations_table.name,
    ResourcesTable     = aws_dynamodb_table.resources_table.name,
    BookingsTable      = aws_dynamodb_table.bookings_table.name,
    RestAPI            = "${local.resource_name_prefix}-api"
    ApplicationName    = var.serverless_application_name
  })
}
