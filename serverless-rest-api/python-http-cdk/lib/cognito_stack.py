# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    core as cdk,
    aws_cognito as cognito
)
from aws_cdk.aws_cognito import CfnUserPool, CfnUserPoolClient


class CognitoStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, admin_group_name="apiAdmins", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        user_pool = CfnUserPool(
            self, "UserPoolInstance",
            user_pool_name=self.stack_name+"-UserPool",
            admin_create_user_config={'allowAdminCreateUserOnly': False},
            schema=[
                {
                    'attribute_data_type': 'String',
                    'name': 'name',
                    'mutable': True,
                    'required': True,
                },
                {
                    'attribute_data_type': 'String',
                    'name': 'email',
                    'mutable': True,
                    'required': True,
                },
            ],
            username_attributes=['email'],
        )
        user_pool_client = CfnUserPoolClient(
            self, "UserPoolClientInstance",
            client_name=self.stack_name+"UserPoolClient",
            user_pool_id=user_pool.ref,
            explicit_auth_flows=['ALLOW_USER_PASSWORD_AUTH','ALLOW_USER_SRP_AUTH','ALLOW_REFRESH_TOKEN_AUTH'],
            generate_secret=False,
            prevent_user_existence_errors='ENABLED',
            refresh_token_validity=30,
            supported_identity_providers=['COGNITO'],
            allowed_o_auth_flows_user_pool_client=True,
            allowed_o_auth_flows=['code'],
            allowed_o_auth_scopes=['email','openid'],
            callback_ur_ls=['http://localhost'],
        )
        user_pool_admin_group = cognito.CfnUserPoolGroup(
            self, "AdminUserPoolGroupInstance",
            user_pool_id=user_pool.ref,
            group_name=admin_group_name,
            description="User group for API Administrators",
            precedence=0
        )
        stack_name_prefix=self.stack_name.replace('-', '')
        cdk.CfnOutput(self, stack_name_prefix+'UserPool', export_name=stack_name_prefix+'UserPool', value=user_pool.ref, description='Cognito User Pool ID')
        cdk.CfnOutput(self, stack_name_prefix+'UserPoolClient', export_name=stack_name_prefix+'UserPoolClient', value=user_pool_client.ref, description='Cognito User Pool Application Client ID')
        cdk.CfnOutput(self, stack_name_prefix+'UserPoolAdminGroupName', export_name=stack_name_prefix+'UserPoolAdminGroupName', value=user_pool_admin_group.group_name, description='User Pool group name for API administrators')
        cdk.CfnOutput(self, stack_name_prefix+'CognitoLoginURL', export_name=stack_name_prefix+'CognitoLoginURL', value=f'https://${user_pool_client.ref}.auth.{cdk.Aws.REGION}.amazoncognito.com/login?client_id={user_pool_client.ref}&response_type=code&redirect_uri=http://localhost', description='Cognito User Pool Application Client Hosted Login UI URL')
        cdk.CfnOutput(self, stack_name_prefix+'CognitoAuthCommand', export_name=stack_name_prefix+'CognitoAuthCommand', value=f'aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id {user_pool_client.ref} --auth-parameters USERNAME=<username>,PASSWORD=<password>', description='AWS CLI command for Amazon Cognito User Pool authentication')

