# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
import os
from random import *
import aws_cdk as cdk

from lib.apigw_queue_ingestion import APIgwQueueIngestionStack
from lib.cognito_stack import CognitoStack
from lib.pipeline_stack import ApiPipelineStack


#NOTE: API_STACK_NAME inside app.py is used to create S3 Bucket with same name,  so if error duplicate bucket name error observed during cdk deploy
     # then please update API_STACK_NAME variable with unique name and run cdk synth and cdk deploy commands again.
     # Keep Stack Name less than 20 characters.
API_STACK_NAME = "apigw-queue-cdk-66"
COGNITO_STACK_NAME = API_STACK_NAME+"-cognito"
PIPELINE_STACK_NAME = API_STACK_NAME+"-pipeline"

app = cdk.App()

# Shared Cognito stack
cognito_stack = CognitoStack(app, COGNITO_STACK_NAME, description='Cognito stack for API Gateway Lambda Authorizer')
cdk.Tags.of(cognito_stack).add('Stack', cdk.Aws.STACK_NAME)


APIgwQueueIngestionStack(app, API_STACK_NAME, cognito_stack_name=cognito_stack.stack_name)

# CI/CD that uses CDK pipeline - https://docs.aws.amazon.com/cdk/api/latest/docs/pipelines-readme.html
cdk_pipeline_stack = ApiPipelineStack(app, PIPELINE_STACK_NAME)
cdk.Tags.of(cdk_pipeline_stack).add('Stack', cdk.Aws.STACK_NAME)

app.synth()
