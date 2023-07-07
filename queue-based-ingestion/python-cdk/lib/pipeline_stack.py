# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import aws_cdk as cdk

from aws_cdk import (
    Stack,
    aws_iam as iam,
     Stack,
    Stage,
    aws_codepipeline as codepipeline,
    pipelines,
    aws_codecommit as codecommit ,
    aws_codepipeline_actions as codepipeline_actions
)

from aws_cdk.pipelines import CodePipeline
from aws_cdk.aws_codepipeline_actions import CodeCommitTrigger
from constructs import Construct

from lib.apigw_queue_ingestion import APIgwQueueIngestionStack
from lib.cognito_stack import CognitoStack


class AppStage(Stage):
    def __init__(self, scope: Construct, id: str, cognito_stack_name="", **kwargs):
        super().__init__(scope, id, **kwargs)
        self.cognito_stack_name = cognito_stack_name
        cognito_stack = CognitoStack(self, cognito_stack_name)
        # CDK pipeline prefixed Cognito stack name with Pipeline name automatically, need to address it while passing name to the API stack
        apigw_stack = APIgwQueueIngestionStack(self, "app", cognito_stack_name=id+"-"+cognito_stack_name)
        apigw_stack.add_dependency(cognito_stack)
        self.apigw_queue_ingestion_stack_name = cdk.CfnOutput(apigw_stack, 'stack_name', value=apigw_stack.stack_name)


class ApiPipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        CODECOMMIT_REPO_NAME = cdk.CfnParameter(self, "CodeCommitRepoName",
                                                type="String",
                                                default=self.stack_name,
                                                description="CodeCommit repository with the project code").value_as_string
        
        repository = codecommit.Repository(
                self, 'CodeCommitRepo',
            repository_name= CODECOMMIT_REPO_NAME
        )
        source_output = codepipeline.Artifact()
        
        source_repo = pipelines.CodePipelineSource.code_commit(
                                repository, 
                                "main",
                                trigger=CodeCommitTrigger.EVENTS
                                )

        pipeline =  CodePipeline (self, "Pipeline", 
                        pipeline_name="apigw-queue-ingestion-pipeline",
                        docker_enabled_for_synth=True,
                        synth=pipelines.CodeBuildStep("Synth", 
                            input = source_repo,
                            commands=["npm install -g aws-cdk;",
                                "cd queue-based-ingestion/python-cdk",
                                "pip install -r requirements.txt",
                                "pip install -r ./src/api/requirements.txt", 
                                "cdk synth --output $CODEBUILD_SRC_DIR/cdk.out"],
                            )
                        )        

        # Add testing stage to the pipeline and testing activity with permissions necessary to run integration tests
        integration_stage = AppStage(self, self.stack_name+'-int-test', cognito_stack_name='Cognito')
        integration_testing = pipelines.CodeBuildStep(
            'IntegrationTest',
            input=source_repo,
            commands=[
                'cd queue-based-ingestion/python-cdk',
                'pip install -r ./tests/requirements.txt',
                'pip install -r ./src/api/requirements.txt',
                'python -m pytest tests/integration -v'
            ],
            env_from_cfn_outputs={
                    "TEST_APPLICATION_STACK_NAME": integration_stage.apigw_queue_ingestion_stack_name
                },
            role_policy_statements=[
                iam.PolicyStatement(
                    actions=['cognito-idp:AdminDeleteUser',
                    'cognito-idp:AdminConfirmSignUp',
                    'cognito-idp:AdminAddUserToGroup'
                    ],
                    resources=[f'arn:aws:cognito-idp:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:userpool/*'],
                ),
                iam.PolicyStatement(
                    actions=["secretsmanager:GetRandomPassword"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=["dynamodb:*"],
                    resources=[f'arn:aws:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/job-reqeust-store-{integration_stage.stage_name}*'],
                ),
                iam.PolicyStatement(
                    actions=["cloudformation:DescribeStacks"],
                    resources=[f'arn:aws:cloudformation:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:stack/{integration_stage.stage_name}*/*',
                    f'arn:aws:cloudformation:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:stack/{integration_stage.cognito_stack_name}/*'],
                ),            
            ]
        )
        pipeline.add_stage(integration_stage,
           post=[
                integration_testing
            ]
        )

        # Create production deployment stage to the pipeline with manual approval action
        deployment_stage = AppStage(self, self.stack_name+'-deploy', cognito_stack_name='Cognito')
        
        manual_approval_step= pipelines.ManualApprovalStep('ApproveProductionDeployment')

        pipeline_deployment_stage = pipeline.add_stage(deployment_stage,
            pre=[
                manual_approval_step
            ]
        )