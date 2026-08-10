terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  profile = var.aws_profile
  region  = var.aws_region
}

# --- REST API (defined via OpenAPI body to support responseTransferMode) ---

resource "aws_api_gateway_rest_api" "api" {
  name = "sse-chatbot-demo"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  body = jsonencode({
    openapi = "3.0.1"
    info = {
      title   = "sse-chatbot-demo"
      version = "1.0"
    }
    paths = {
      "/chat" = {
        post = {
          x-amazon-apigateway-integration = {
            type                 = "aws_proxy"
            httpMethod           = "POST"
            uri                  = replace(replace(aws_lambda_function.chat.invoke_arn, "2015-03-31", "2021-11-15"), "/invocations", "/response-streaming-invocations")
            passthroughBehavior  = "when_no_match"
            responseTransferMode = "STREAM"
          }
        }
        options = {
          summary = "CORS preflight"
          responses = {
            "200" = {
              description = "CORS preflight response"
              headers = {
                "Access-Control-Allow-Origin" = {
                  schema = { type = "string" }
                }
                "Access-Control-Allow-Methods" = {
                  schema = { type = "string" }
                }
                "Access-Control-Allow-Headers" = {
                  schema = { type = "string" }
                }
              }
            }
          }
          x-amazon-apigateway-integration = {
            type = "mock"
            requestTemplates = {
              "application/json" = "{\"statusCode\": 200}"
            }
            responses = {
              default = {
                statusCode = "200"
                responseParameters = {
                  "method.response.header.Access-Control-Allow-Origin"  = "'*'"
                  "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
                  "method.response.header.Access-Control-Allow-Headers" = "'Content-Type'"
                }
              }
            }
          }
        }
      }
    }
  })
}

# --- Deployment & Stage ---

resource "aws_api_gateway_deployment" "deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = md5(jsonencode(aws_api_gateway_rest_api.api.body))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "demo" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.deployment.id
  stage_name    = "demo"
}
