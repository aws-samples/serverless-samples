# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk.core import Stack, Construct, Stage
from aws_cdk.pipelines import CdkPipeline, SimpleSynthAction, ShellScriptAction

import aws_cdk.core as cdk
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_iam as iam
from serverless_api_stack import ServerlessApiStack
from lib.cognito_stack import CognitoStack


class AppStage(Stage):
    def __init__(self, scope: Construct, id: str, cognito_stack_name="", **kwargs):
        super().__init__(scope, id, **kwargs)
        self.cognito_stack_name = cognito_stack_name
        cognito_stack = CognitoStack(self, cognito_stack_name)
        # CDK pipeline prefixed Cognito stack name with Pipeline name automatically, need to address it while passing name to the API stack
        api_stack = ServerlessApiStack(self, "Api", cognito_stack_name=id+"-"+cognito_stack_name)
        api_stack.add_dependency(cognito_stack)
        self.api_stack_name = cdk.CfnOutput(api_stack, 'stack_name', value=api_stack.stack_name)


class ApiPipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        CODECOMMIT_REPO_NAME = cdk.CfnParameter(self, "CodeCommitRepoName",
                                                type="String",
                                                default="serverless-api-pipeline-cdk",
                                                description="CodeCommit repository with the project code").value_as_string

        PIPELINE_NAME = "serverless-api-pipeline-cdk"

        source_artifact = codepipeline.Artifact()
        cloud_assembly_artifact = codepipeline.Artifact()

        pipeline = CdkPipeline(self, "Pipeline",
                               pipeline_name=PIPELINE_NAME,
                               cloud_assembly_artifact=cloud_assembly_artifact,
                               source_action=codepipeline_actions.CodeCommitSourceAction(
                                   action_name="CodeCommit",
                                   output=source_artifact,
                                   branch='main',
                                   trigger=codepipeline_actions.CodeCommitTrigger.POLL,
                                   repository=codecommit.Repository(self, 'ServerlessApiRepository',
                                                                    repository_name=CODECOMMIT_REPO_NAME)
                               ),
                               synth_action=SimpleSynthAction.standard_npm_synth(
                                   source_artifact=source_artifact,
                                   cloud_assembly_artifact=cloud_assembly_artifact,

                                   environment={'privileged': True},
                                   install_command='cd ./serverless-rest-api/python-http-cdk; npm install -g aws-cdk; pip install -r requirements.txt; pip install -r ./src/api/requirements.txt ',
                                   synth_command='cdk synth --output $CODEBUILD_SRC_DIR/cdk.out'
                               )
                               )

        # Add testing stage to the pipeline and testing activity with permissions necessary to run integration tests
        testing_stage = AppStage(self, 'serverless-api-pipeline-cdk-Testing', cognito_stack_name='Cognito')
        pipeline_testing_stage = pipeline.add_application_stage(testing_stage)
        testing_action = ShellScriptAction(
            action_name='IntegrationTest',
            additional_artifacts=[source_artifact],
            commands=[
                'cd ./serverless-rest-api/python-http-cdk',
                'pip install -r ./tests/requirements.txt',
                'pip install -r ./src/api/requirements.txt',
                'python -m pytest tests/integration -v'
            ],
            use_outputs={
                'TEST_APPLICATION_STACK_NAME': pipeline.stack_output(testing_stage.api_stack_name)
            },
        )
        pipeline_testing_stage.add_actions(testing_action)
        testing_action.project.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'cognito-idp:AdminDeleteUser',
                'cognito-idp:AdminConfirmSignUp',
                'cognito-idp:AdminAddUserToGroup'
            ],
            resources=[f'arn:aws:cognito-idp:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:userpool/*'],
        )
        )
        testing_action.project.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['secretsmanager:GetRandomPassword'],
            resources=['*'],
        )
        )
        testing_action.project.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['dynamodb:*'],
            resources=[f'arn:aws:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{testing_stage.stage_name}*'],
        )
        )
        testing_action.project.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['cloudformation:DescribeStacks'],
            resources=[
                f'arn:aws:cloudformation:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:stack/{testing_stage.stage_name}*/*',
                f'arn:aws:cloudformation:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:stack/{testing_stage.cognito_stack_name}/*'
                ],
        )
        )

        # Create production deployment stage to the pipeline with manual approval action
        deployment_stage = AppStage(self, 'serverless-api-pipeline-cdk-Deployment', cognito_stack_name='Cognito')
        pipeline_deployment_stage = pipeline.add_application_stage(deployment_stage)
        pipeline_deployment_stage.add_actions(
            codepipeline_actions.ManualApprovalAction(action_name='ApproveProductionDeployment', run_order=1)
        )
