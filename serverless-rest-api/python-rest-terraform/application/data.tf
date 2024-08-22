# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "lambda_role_policy_document" {
  statement {
    sid = "lambdarolepolicydocument"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:DeleteItem",
      "dynamodb:PutItem",
      "dynamodb:Scan",
      "dynamodb:Query",
      "dynamodb:UpdateItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:BatchGetItem",
      "dynamodb:DescribeTable",
      "dynamodb:ConditionCheckItem"
    ]

    resources = [
      "${aws_dynamodb_table.locations_table.arn}",
      "${aws_dynamodb_table.locations_table.arn}/index/*",
      "${aws_dynamodb_table.resources_table.arn}",
      "${aws_dynamodb_table.resources_table.arn}/index/*",
      "${aws_dynamodb_table.bookings_table.arn}",
      "${aws_dynamodb_table.bookings_table.arn}/index/*"
    ]
  }
}


data "aws_iam_policy_document" "api_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "lambda_authorizer_role_policy_document" {
  statement {
    sid = "lambdaauthorizerrolepolicydocument"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = [
      "${module.lambda_functions["authorizer"].lambda_function_arn}"
    ]
  }
}

data "aws_iam_policy" "api_cloudwatch_logging" {
  arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

data "aws_cloudformation_stack" "cognito_stack" {
  name = var.cognito_stack_name
}
