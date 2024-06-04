# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import botocore.session
from aws_lambda_powertools import Logger

logger = Logger()

resource_access_role_arn = os.environ.get('RESOURCE_ACCESS_ROLE_ARN')

sts = boto3.client('sts')


class UserAbacSession(object):
    def __init__(self, user_id: str) -> None:
        if not user_id:
            raise ValueError("user_id missing")

        self._user_id = user_id

        # Assume the ResourceAccessRole, and set the requested user_id
        # as a session tag.
        assume_role_response = sts.assume_role(
            RoleArn=resource_access_role_arn,
            RoleSessionName=f"demo-user-session-{self._user_id}",
            DurationSeconds=900,
            Tags=[{'Key': 'UserID', 'Value': self._user_id}],
        )
        logger.debug(f"Assume role response: {assume_role_response}")

        # Create a botocore session object with the credentials from the
        # assumed role.
        self._botocore_session = botocore.session.get_session()
        self._botocore_session.set_credentials(
            access_key=assume_role_response['Credentials']['AccessKeyId'],
            secret_key=assume_role_response['Credentials']['SecretAccessKey'],
            token=assume_role_response['Credentials']['SessionToken'],
        )

        # Also create a matching boto3 session object
        self._boto3_session = boto3.Session(
            botocore_session=self._botocore_session
        )
        logger.info(f"Session initialised: demo-user-session-{self._user_id}")

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def botocore_session(self) -> botocore.session:
        return self._botocore_session

    @property
    def boto3_session(self) -> boto3.Session:
        return self._boto3_session
