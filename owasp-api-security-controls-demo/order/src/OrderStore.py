# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from aws_lambda_powertools import Logger
from datetime import datetime, timezone
from typing import Dict
from boto3.dynamodb.conditions import Key
from UserAbacSession import UserAbacSession

logger = Logger()

order_table_name = os.environ.get('ORDER_TABLE_NAME')
ddb_vpce_dns = os.environ.get('DDB_VPCE_DNS_NAME')


class OrderStore(object):
    def __init__(self, user_session: UserAbacSession, is_admin) -> None:
        self._user_session = user_session
        self._is_admin = is_admin

        self._resource = self._user_session.boto3_session.resource('dynamodb', endpoint_url=f"https://{ddb_vpce_dns}")
        self._table = self._resource.Table(order_table_name)
        logger.info("OrderStore initiatised.")

    def retrieve(self) -> Dict:
        if self._is_admin:
            response = self._table.scan(Limit=5)
        else:
            response = self._table.query(
                KeyConditionExpression=Key('user_id').eq(
                    self._user_session.user_id))
        logger.info("response", extra={'response': response})
        return response.get('Items', {})

    def store(self, data: Dict) -> Dict:
        item = {
            **data,
            'user_id': self._user_session.user_id,
            'order_date': datetime.now(timezone.utc).isoformat(),
        }
        response = self._table.put_item(Item=item)
        logger.info("response", extra={'response': response})
        return item
