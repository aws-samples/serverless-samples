# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    core as cdk,
    aws_dynamodb as ddb,
    aws_lambda as lmbd,
    aws_apigatewayv2 as httpapi,
    aws_logs as logs,
    aws_sns as sns,
    aws_cloudwatch as cwl
)
from aws_cdk.aws_lambda_python import PythonFunction
from aws_cdk.aws_apigatewayv2_integrations import LambdaProxyIntegration
from aws_cdk.aws_apigatewayv2_authorizers import HttpLambdaAuthorizer
from aws_cdk.aws_cloudwatch_actions import SnsAction


class ServerlessApiStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, cognito_stack_name="", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.cognito_stack_name = cognito_stack_name
        # check if Cognito stack name was passed as a stack parameter instead
        if cognito_stack_name == "":
            upload_bucket_name = cdk.CfnParameter(self, "CognitoStackName", type="String",
                                                  description="The name of the Cognito stack to be used by API Lambda Authorizer.")
        # use default value if nothing else works
        if cognito_stack_name == "":
            self.cognito_stack_name = "apigw - samples - cognito - shared"

        # Create DynamoDB tables and GSIs for the API
        locations_table = ddb.Table(self, 'LocationsTable',
                                    partition_key=ddb.Attribute(name='locationid', type=ddb.AttributeType.STRING)
                                    )
        resources_table = ddb.Table(self, 'ResourcesTable',
                                    partition_key=ddb.Attribute(name='resourceid', type=ddb.AttributeType.STRING)
                                    )
        resources_table.add_global_secondary_index(index_name='locationidGSI',
                                                   partition_key=ddb.Attribute(name='locationid',
                                                                               type=ddb.AttributeType.STRING),
                                                   projection_type=ddb.ProjectionType.ALL
                                                   )
        bookings_table = ddb.Table(self, 'BookingsTable',
                                   partition_key=ddb.Attribute(name='bookingid', type=ddb.AttributeType.STRING)
                                   )
        bookings_table.add_global_secondary_index(index_name='useridGSI',
                                                  partition_key=ddb.Attribute(name='userid',
                                                                              type=ddb.AttributeType.STRING),
                                                  projection_type=ddb.ProjectionType.ALL
                                                  )
        bookings_table.add_global_secondary_index(index_name='bookingsByUserByTimeGSI',
                                                  partition_key=ddb.Attribute(name='userid',
                                                                              type=ddb.AttributeType.STRING),
                                                  sort_key=ddb.Attribute(name='starttimeepochtime',
                                                                         type=ddb.AttributeType.NUMBER),
                                                  projection_type=ddb.ProjectionType.ALL
                                                  )
        bookings_table.add_global_secondary_index(index_name='bookingsByResourceByTimeGSI',
                                                  partition_key=ddb.Attribute(name='resourceid',
                                                                              type=ddb.AttributeType.STRING),
                                                  sort_key=ddb.Attribute(name='starttimeepochtime',
                                                                         type=ddb.AttributeType.NUMBER),
                                                  projection_type=ddb.ProjectionType.ALL
                                                  )
        # Create CRUD and search Lambda functions for APIs
        locations_lambda_function = PythonFunction(self, 'LocationsFunction',
                                                   entry='src/api',
                                                   index='locations.py',
                                                   handler='lambda_handler',
                                                   runtime=lmbd.Runtime.PYTHON_3_8,
                                                   memory_size=1024,
                                                   tracing=lmbd.Tracing.ACTIVE,
                                                   environment={
                                                       'LOCATIONS_TABLE': locations_table.table_name,
                                                       'AWS_EMF_NAMESPACE': self.stack_name,
                                                       'AWS_XRAY_TRACING_NAME': self.stack_name,
                                                       'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'
                                                   }
                                                   )
        locations_table.grant_read_write_data(locations_lambda_function)
        resources_lambda_function = PythonFunction(self, 'ResourcesFunction',
                                                   entry='src/api',
                                                   index='resources.py',
                                                   handler='lambda_handler',
                                                   runtime=lmbd.Runtime.PYTHON_3_8,
                                                   memory_size=1024,
                                                   tracing=lmbd.Tracing.ACTIVE,
                                                   environment={
                                                       'RESOURCES_TABLE': resources_table.table_name,
                                                       'AWS_EMF_NAMESPACE': self.stack_name,
                                                       'AWS_XRAY_TRACING_NAME': self.stack_name,
                                                       'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'
                                                   }
                                                   )
        resources_table.grant_read_write_data(resources_lambda_function)
        bookings_lambda_function = PythonFunction(self, 'BookingsFunction',
                                                  entry='src/api',
                                                  index='bookings.py',
                                                  handler='lambda_handler',
                                                  runtime=lmbd.Runtime.PYTHON_3_8,
                                                  memory_size=1024,
                                                  tracing=lmbd.Tracing.ACTIVE,
                                                  environment={
                                                      'BOOKINGS_TABLE': bookings_table.table_name,
                                                      'AWS_EMF_NAMESPACE': self.stack_name,
                                                      'AWS_XRAY_TRACING_NAME': self.stack_name,
                                                      'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'
                                                  }
                                                  )
        bookings_table.grant_read_write_data(bookings_lambda_function)
        # Create API with proper authentication/authorization
        cognito_stack_name_prefix = self.cognito_stack_name.replace('-', '')
        authorizer_lambda_function = PythonFunction(self, 'APIAuthorizerFunction',
                                                    entry='src/api',
                                                    index='authorizer.py',
                                                    handler='lambda_handler',
                                                    runtime=lmbd.Runtime.PYTHON_3_8,
                                                    memory_size=1024,
                                                    tracing=lmbd.Tracing.ACTIVE,
                                                    environment={
                                                        'USER_POOL_ID': cdk.Fn.import_value(
                                                            cognito_stack_name_prefix + 'UserPool'),
                                                        'APPLICATION_CLIENT_ID': cdk.Fn.import_value(
                                                            cognito_stack_name_prefix + 'UserPoolClient'),
                                                        'ADMIN_GROUP_NAME': cdk.Fn.import_value(
                                                            cognito_stack_name_prefix + 'UserPoolAdminGroupName'),
                                                        'AWS_XRAY_TRACING_NAME': self.stack_name,
                                                        'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'
                                                    }
                                                    )
        api_lambda_authorizer = HttpLambdaAuthorizer(authorizer_name='ApiLambdaAuthorizer',
                                                     handler=authorizer_lambda_function,
                                                     identity_source=['$request.header.Authorization'])
        api_log_group = logs.LogGroup(self, 'ApiLogs', retention=logs.RetentionDays.ONE_MONTH)
        api = httpapi.HttpApi(self, 'ServiceApi',
                              default_authorizer=api_lambda_authorizer,
                              cors_preflight={
                                  'allow_headers': ['Content-Type', 'Authorization', 'X-Forwarded-For', 'X-Api-Key', 'X-Amz-Date', 'X-Amz-Security-Token'],
                                  'allow_methods': [httpapi.CorsHttpMethod.GET, httpapi.CorsHttpMethod.PUT, httpapi.CorsHttpMethod.DELETE, httpapi.CorsHttpMethod.OPTIONS],
                                  'allow_origins': ['*']
                              }
                              )
        api.default_stage.node.default_child.AccessLogSettingsProperty = {
            'destination_arn': api_log_group.log_group_arn,
            'format': '{ "requestId":"$context.requestId", "ip": "$context.identity.sourceIp", "requestTime":"$context.requestTime", "httpMethod":"$context.httpMethod","routeKey":"$context.routeKey", "status":"$context.status","protocol":"$context.protocol", "integrationStatus": $context.integrationStatus, "integrationLatency": $context.integrationLatency, "responseLength":"$context.responseLength" }'
        }
        api.add_routes(path='/locations',
                       methods=[httpapi.HttpMethod.GET, httpapi.HttpMethod.PUT],
                       integration=LambdaProxyIntegration(handler=locations_lambda_function)
                       )
        api.add_routes(path='/locations/{locationid}',
                       methods=[httpapi.HttpMethod.GET, httpapi.HttpMethod.DELETE],
                       integration=LambdaProxyIntegration(handler=locations_lambda_function)
                       )
        api.add_routes(path='/locations/{locationid}/resources',
                       methods=[httpapi.HttpMethod.GET, httpapi.HttpMethod.PUT],
                       integration=LambdaProxyIntegration(handler=resources_lambda_function)
                       )
        api.add_routes(path='/locations/{locationid}/resources/{resourceid}',
                       methods=[httpapi.HttpMethod.GET, httpapi.HttpMethod.DELETE],
                       integration=LambdaProxyIntegration(handler=resources_lambda_function)
                       )
        api.add_routes(path='/locations/{locationid}/resources/{resourceid}/bookings',
                       methods=[httpapi.HttpMethod.GET],
                       integration=LambdaProxyIntegration(handler=bookings_lambda_function)
                       )
        api.add_routes(path='/users/{userid}/bookings',
                       methods=[httpapi.HttpMethod.GET, httpapi.HttpMethod.PUT],
                       integration=LambdaProxyIntegration(handler=bookings_lambda_function)
                       )
        api.add_routes(path='/users/{userid}/bookings/{bookingid}',
                       methods=[httpapi.HttpMethod.GET, httpapi.HttpMethod.DELETE],
                       integration=LambdaProxyIntegration(handler=bookings_lambda_function)
                       )
        # Create alarms for the API and backend
        alarms_topic = sns.Topic(self, 'AlarmsTopic')
        api_errors_alarm = cwl.Alarm(self, 'HttpApiErrorsAlarm',
                                     metric=cwl.Metric(namespace='AWS/ApiGateway',
                                                       metric_name='5XXError',
                                                       dimensions={'ApiName': api.api_id}),
                                     evaluation_periods=1,
                                     period=cdk.Duration.minutes(1),
                                     statistic='Sum',
                                     threshold=1.0)
        api_errors_alarm.add_alarm_action(SnsAction(alarms_topic))
        authorizer_lambda_errors_alarm = cwl.Alarm(self, 'AuthorizerFunctionErrorsAlarm',
                                                   metric=cwl.Metric(namespace='AWS/Lambda',
                                                                     metric_name='Errors',
                                                                     dimensions={
                                                                         'FunctionName': authorizer_lambda_function.function_name}),
                                                   evaluation_periods=1,
                                                   period=cdk.Duration.minutes(1),
                                                   statistic='Sum',
                                                   threshold=1.0)
        authorizer_lambda_errors_alarm.add_alarm_action(SnsAction(alarms_topic))
        authorizer_lambda_throttling_alarm = cwl.Alarm(self, 'AuthorizerFunctionThrottlingAlarm',
                                                       metric=cwl.Metric(namespace='AWS/Lambda',
                                                                         metric_name='Throttles',
                                                                         dimensions={
                                                                             'FunctionName': authorizer_lambda_function.function_name}),
                                                       evaluation_periods=1,
                                                       period=cdk.Duration.minutes(1),
                                                       statistic='Sum',
                                                       threshold=1.0)
        authorizer_lambda_throttling_alarm.add_alarm_action(SnsAction(alarms_topic))
        locations_lambda_errors_alarm = cwl.Alarm(self, 'LocationsFunctionErrorsAlarm',
                                                  metric=cwl.Metric(namespace='AWS/Lambda',
                                                                    metric_name='Errors',
                                                                    dimensions={
                                                                        'FunctionName': locations_lambda_function.function_name}),
                                                  evaluation_periods=1,
                                                  period=cdk.Duration.minutes(1),
                                                  statistic='Sum',
                                                  threshold=1.0)
        locations_lambda_errors_alarm.add_alarm_action(SnsAction(alarms_topic))
        locations_lambda_throttling_alarm = cwl.Alarm(self, 'LocationsFunctionThrottlingAlarm',
                                                      metric=cwl.Metric(namespace='AWS/Lambda',
                                                                        metric_name='Throttles',
                                                                        dimensions={
                                                                            'FunctionName': locations_lambda_function.function_name}),
                                                      evaluation_periods=1,
                                                      period=cdk.Duration.minutes(1),
                                                      statistic='Sum',
                                                      threshold=1.0)
        locations_lambda_throttling_alarm.add_alarm_action(SnsAction(alarms_topic))
        resources_lambda_errors_alarm = cwl.Alarm(self, 'ResourcesFunctionErrorsAlarm',
                                                  metric=cwl.Metric(namespace='AWS/Lambda',
                                                                    metric_name='Errors',
                                                                    dimensions={
                                                                        'FunctionName': resources_lambda_function.function_name}),
                                                  evaluation_periods=1,
                                                  period=cdk.Duration.minutes(1),
                                                  statistic='Sum',
                                                  threshold=1.0)
        resources_lambda_errors_alarm.add_alarm_action(SnsAction(alarms_topic))
        resources_lambda_throttling_alarm = cwl.Alarm(self, 'ResourcesFunctionThrottlingAlarm',
                                                      metric=cwl.Metric(namespace='AWS/Lambda',
                                                                        metric_name='Throttles',
                                                                        dimensions={
                                                                            'FunctionName': resources_lambda_function.function_name}),
                                                      evaluation_periods=1,
                                                      period=cdk.Duration.minutes(1),
                                                      statistic='Sum',
                                                      threshold=1.0)
        resources_lambda_throttling_alarm.add_alarm_action(SnsAction(alarms_topic))
        bookings_lambda_errors_alarm = cwl.Alarm(self, 'BookingsFunctionErrorsAlarm',
                                                 metric=cwl.Metric(namespace='AWS/Lambda',
                                                                   metric_name='Errors',
                                                                   dimensions={
                                                                       'FunctionName': bookings_lambda_function.function_name}),
                                                 evaluation_periods=1,
                                                 period=cdk.Duration.minutes(1),
                                                 statistic='Sum',
                                                 threshold=1.0)
        bookings_lambda_errors_alarm.add_alarm_action(SnsAction(alarms_topic))
        bookings_lambda_throttling_alarm = cwl.Alarm(self, 'BookingsFunctionThrottlingAlarm',
                                                     metric=cwl.Metric(namespace='AWS/Lambda',
                                                                       metric_name='Throttles',
                                                                       dimensions={
                                                                           'FunctionName': bookings_lambda_function.function_name}),
                                                     evaluation_periods=1,
                                                     period=cdk.Duration.minutes(1),
                                                     statistic='Sum',
                                                     threshold=1.0)
        bookings_lambda_throttling_alarm.add_alarm_action(SnsAction(alarms_topic))
        locations_table_throttling_alarm = cwl.Alarm(self, 'LocationsDynamoDBThrottlingAlarm',
                                                     metric=cwl.Metric(namespace='AWS/DynamoDB',
                                                                       metric_name='ThrottledRequests',
                                                                       dimensions={
                                                                           'FunctionName': locations_table.table_name}),
                                                     evaluation_periods=1,
                                                     period=cdk.Duration.minutes(1),
                                                     statistic='Sum',
                                                     threshold=1.0)
        locations_table_throttling_alarm.add_alarm_action(SnsAction(alarms_topic))
        resources_table_throttling_alarm = cwl.Alarm(self, 'ResourcesDynamoDBThrottlingAlarm',
                                                     metric=cwl.Metric(namespace='AWS/DynamoDB',
                                                                       metric_name='ThrottledRequests',
                                                                       dimensions={
                                                                           'FunctionName': resources_table.table_name}),
                                                     evaluation_periods=1,
                                                     period=cdk.Duration.minutes(1),
                                                     statistic='Sum',
                                                     threshold=1.0)
        resources_table_throttling_alarm.add_alarm_action(SnsAction(alarms_topic))
        bookings_table_throttling_alarm = cwl.Alarm(self, 'BookingsDynamoDBThrottlingAlarm',
                                                    metric=cwl.Metric(namespace='AWS/DynamoDB',
                                                                      metric_name='ThrottledRequests',
                                                                      dimensions={
                                                                          'FunctionName': bookings_table.table_name}),
                                                    evaluation_periods=1,
                                                    period=cdk.Duration.minutes(1),
                                                    statistic='Sum',
                                                    threshold=1.0)
        bookings_table_throttling_alarm.add_alarm_action(SnsAction(alarms_topic))
        # Create dashboard
        application_dashboard = cwl.Dashboard(self, 'ApplicationDashboard',
                                              dashboard_name=self.stack_name + '-Dashboard')
        application_dashboard.add_widgets(
            cwl.GraphWidget(title='Business Metrics',
                            width=12,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace=self.stack_name,
                                    metric_name='ProcessedBookings',
                                    dimensions={
                                        'ServiceName': bookings_lambda_function.function_name,
                                        'LogGroup': bookings_lambda_function.function_name,
                                        'ServiceType': 'AWS::Lambda::Function',
                                        'Service': 'Bookings'
                                    },
                                    label='Processed Bookings',
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace=self.stack_name,
                                    metric_name='ProcessedLocations',
                                    dimensions={
                                        'ServiceName': locations_lambda_function.function_name,
                                        'LogGroup': locations_lambda_function.function_name,
                                        'ServiceType': 'AWS::Lambda::Function',
                                        'Service': 'Locations'
                                    },
                                    label='Processed Locations',
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace=self.stack_name,
                                    metric_name='ProcessedResources',
                                    dimensions={
                                        'ServiceName': resources_lambda_function.function_name,
                                        'LogGroup': resources_lambda_function.function_name,
                                        'ServiceType': 'AWS::Lambda::Function',
                                        'Service': 'Resources'
                                    },
                                    label='Processed Resources',
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                            ]
                            ),
            cwl.GraphWidget(title='API Gateway',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='DataProcessed',
                                    dimensions={'ApiId': api.api_id},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='IntegrationLatency',
                                    dimensions={'ApiId': api.api_id},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='Latency',
                                    dimensions={'ApiId': api.api_id},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                            ],
                            right=[
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='4xx',
                                    dimensions={'ApiId': api.api_id},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='5xx',
                                    dimensions={'ApiId': api.api_id},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='Count',
                                    dimensions={'ApiId': api.api_id},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                            ]
                            )
        )
        application_dashboard.add_widgets(
            cwl.GraphWidget(title='Locations Lambda',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Invocations',
                                    dimensions={
                                        'FunctionName': locations_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Errors',
                                    dimensions={
                                        'FunctionName': locations_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Throttles',
                                    dimensions={
                                        'FunctionName': locations_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Duration',
                                    dimensions={
                                        'FunctionName': locations_lambda_function.function_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='ConcurrentExecutions',
                                    dimensions={
                                        'FunctionName': locations_lambda_function.function_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                )
                            ]
                            ),
            cwl.GraphWidget(title='Resources Lambda',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Invocations',
                                    dimensions={
                                        'FunctionName': resources_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Errors',
                                    dimensions={
                                        'FunctionName': resources_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Throttles',
                                    dimensions={
                                        'FunctionName': resources_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Duration',
                                    dimensions={
                                        'FunctionName': resources_lambda_function.function_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='ConcurrentExecutions',
                                    dimensions={
                                        'FunctionName': resources_lambda_function.function_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                )
                            ]
                            ),
            cwl.GraphWidget(title='Bookings Lambda',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Invocations',
                                    dimensions={
                                        'FunctionName': bookings_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Errors',
                                    dimensions={
                                        'FunctionName': bookings_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Throttles',
                                    dimensions={
                                        'FunctionName': bookings_lambda_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Duration',
                                    dimensions={
                                        'FunctionName': bookings_lambda_function.function_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='ConcurrentExecutions',
                                    dimensions={
                                        'FunctionName': bookings_lambda_function.function_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                )
                            ]
                            )
        )
        application_dashboard.add_widgets(
            cwl.GraphWidget(title='DynamoDB - Locations',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ConsumedReadCapacityUnits',
                                    dimensions={
                                        'TableName': locations_table.table_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ConsumedWriteCapacityUnits',
                                    dimensions={
                                        'TableName': locations_table.table_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ProvisionedReadCapacityUnits',
                                    dimensions={
                                        'TableName': locations_table.table_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(5)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ProvisionedWriteCapacityUnits',
                                    dimensions={
                                        'TableName': locations_table.table_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(5)
                                )
                            ]
                            ),
            cwl.GraphWidget(title='DynamoDB - Resources',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ConsumedReadCapacityUnits',
                                    dimensions={
                                        'TableName': resources_table.table_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ConsumedWriteCapacityUnits',
                                    dimensions={
                                        'TableName': resources_table.table_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ProvisionedReadCapacityUnits',
                                    dimensions={
                                        'TableName': resources_table.table_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(5)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ProvisionedWriteCapacityUnits',
                                    dimensions={
                                        'TableName': resources_table.table_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(5)
                                ),
                            ]
                            ),
            cwl.GraphWidget(title='DynamoDB - Bookings',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ConsumedReadCapacityUnits',
                                    dimensions={
                                        'TableName': bookings_table.table_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ConsumedWriteCapacityUnits',
                                    dimensions={
                                        'TableName': bookings_table.table_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ProvisionedReadCapacityUnits',
                                    dimensions={
                                        'TableName': bookings_table.table_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(5)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ProvisionedWriteCapacityUnits',
                                    dimensions={
                                        'TableName': bookings_table.table_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(5)
                                ),
                            ]
                            )
        )
        # Get stack outputs
        cdk.CfnOutput(self, 'LocationsTableName', export_name=self.stack_name + '-LocationsTableName',
                      value=locations_table.table_name, description='DynamoDB Locations table')
        cdk.CfnOutput(self, 'ResourcesTableName', export_name=self.stack_name + '-ResourcesTableName',
                      value=resources_table.table_name, description='DynamoDB Resources table')
        cdk.CfnOutput(self, 'BookingsTableName', export_name=self.stack_name + '-BookingsTableName',
                      value=bookings_table.table_name, description='DynamoDB Bookings table')
        cdk.CfnOutput(self, 'AlarmsTopicARN', export_name=self.stack_name + '-AlarmsTopicARN',
                      value=alarms_topic.topic_arn, description='SNS Topic to be used for the alarms subscriptions')
        cdk.CfnOutput(self, 'AccessLogsGroupARN', export_name=self.stack_name + '-AccessLogsGroupARN',
                      value=api_log_group.log_group_arn,
                      description='CloudWatch Logs group for API Gateway access logs')
        cdk.CfnOutput(self, 'DashboardURL', export_name=self.stack_name + '-DashboardURL',
                      value=f'https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={application_dashboard.node.default_child.dashboard_name}',
                      description='Dashboard URL')
        cdk.CfnOutput(self, 'APIEndpointURL', export_name=self.stack_name + '-APIEndpointURL', value=api.url,
                      description='API Gateway endpoint URL')
        cdk.CfnOutput(self, 'ApiAuthCognitoStackName', export_name=self.stack_name + '-ApiAuthCognitoStackName',
                      value=self.cognito_stack_name, description='Cognito stack used by the API')
