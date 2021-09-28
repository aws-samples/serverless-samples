# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
import os

from aws_cdk import core
from lib.serverless_api_stack import ServerlessApiStack
from lib.pipeline_stack import ApiPipelineStack
from lib.cognito_stack import CognitoStack

API_STACK_NAME = "apigw-samples-cdk"
COGNITO_STACK_NAME = API_STACK_NAME+"-cognito"
PIPELINE_STACK_NAME = API_STACK_NAME+"-pipeline"

app = core.App()
# Shared Cognito stack
cognito_stack = CognitoStack(app, COGNITO_STACK_NAME, description='Cognito stack for API Gateway Lambda Authorizer')
core.Tags.of(cognito_stack).add('Stack', core.Aws.STACK_NAME)

# API stack with all resources necessary
api_stack = ServerlessApiStack(app, API_STACK_NAME, cognito_stack_name=cognito_stack.stack_name, description='Backend API with Lambda and DynamoDB, Lambda Authorizer')
core.Tags.of(api_stack).add('Stack', core.Aws.STACK_NAME)

# CI/CD that uses CDK pipeline - https://docs.aws.amazon.com/cdk/api/latest/docs/pipelines-readme.html
cdk_pipeline_stack = ApiPipelineStack(app, PIPELINE_STACK_NAME)
core.Tags.of(cdk_pipeline_stack).add('Stack', core.Aws.STACK_NAME)

app.synth()
