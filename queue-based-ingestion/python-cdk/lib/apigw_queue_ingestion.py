# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import aws_cdk as cdk

from aws_cdk import (
    Stack,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_source, 
    Aws, Stack,
    BundlingOptions,
    aws_dynamodb as ddb, 
    aws_s3 as s3,
    aws_logs as logs,
    aws_cloudwatch as cwl
)
from constructs import Construct
class APIgwQueueIngestionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, cognito_stack_name="", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        job_request_queue = sqs.Queue(self, "job-request-queue", queue_name="job-request-queue-"+self.stack_name, visibility_timeout=cdk.Duration.seconds(200))

        #Create the API GW service role with permissions to call SQS
        rest_api_role = iam.Role(
            self,
            "JobRequestAPIRole-"+self.stack_name,
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSQSFullAccess")
            ]
            
        )

        api_lambda_authorizer = APIgwQueueIngestionStack.create_api_authorizer_fn(self, cognito_stack_name)
        
        #API authorizer instance 
        authorizer = apigw.TokenAuthorizer(self, "MyAuthorizer",
            handler=api_lambda_authorizer,
            identity_source=apigw.IdentitySource.header('Authorization')
            )

        #Create an API GW Rest API
        base_api= APIgwQueueIngestionStack.create_rest_api_base(self,authorizer)
        api_resource = APIgwQueueIngestionStack.create_rest_api_submit_job(self,base_api,rest_api_role, job_request_queue)

        #Create S3 Bucket 
        job_output_payload_s3 =APIgwQueueIngestionStack.create_job_output_payload_s3(self)

        #create Batch Simulator Function
        batch_simulator_function =APIgwQueueIngestionStack.create_batch_simulator_function(self, job_output_payload_s3)
    
        #Add Read Write persmission on S3 for Lambda Function 
        job_output_payload_s3.grant_read_write(batch_simulator_function)

        #Create DynamoDB Table to store SQS messages
        sqs_msg_store_ddb_tbl = APIgwQueueIngestionStack.create_msg_store_DDB_table(self)

        #Creating Lambda function that will process message from SQS Queue and use batch simulator
        sqs_processor_lambda = APIgwQueueIngestionStack.create_sqs_processor_function(self, sqs_msg_store_ddb_tbl, job_request_queue, batch_simulator_function)
        
        #Add Read Write persmission on table for Lambda Function
        sqs_msg_store_ddb_tbl.grant_read_write_data(sqs_processor_lambda)

        #Allow SQS Processor Lambda to invoke Batch Simulator Lambda function
        batch_simulator_function.grant_invoke(sqs_processor_lambda.role)

        #create get job status function 
        get_job_status_function = APIgwQueueIngestionStack.create_get_job_status_function(self, sqs_msg_store_ddb_tbl)

        #Add Read  persmission on table for Lambda Function
        sqs_msg_store_ddb_tbl.grant_read_data(get_job_status_function)

        #Add Read Write persmission on S3 for Lambda Function 
        job_output_payload_s3.grant_read_write(get_job_status_function)

        method_response_lambda = apigw.MethodResponse(status_code="200")

        get_job_api_resource= base_api.root.add_resource('job-status')
        get_job_api_resource_with_id = get_job_api_resource.add_resource('{job-id}')
        get_job_api_resource_with_id.add_method(
            "GET", 
            apigw.LambdaIntegration(get_job_status_function),
            method_responses=[method_response_lambda]
            )

        APIgwQueueIngestionStack.create_cw_dashboard(self,base_api, sqs_processor_lambda,  get_job_status_function, batch_simulator_function, sqs_msg_store_ddb_tbl)

        cdk.CfnOutput(self, 'ApiAuthCognitoStackName', export_name=self.stack_name + '-ApiAuthCognitoStackName',
            value=self.cognito_stack_name, description='Cognito stack used by the API')
        cdk.CfnOutput(self, 'APIEndpointURL', export_name=self.stack_name + '-APIEndpointURL', value=base_api.url,
                      description='API Gateway endpoint URL')


    @staticmethod
    def create_api_authorizer_fn(this, cognito_stack_name) -> None:
        
        this.cognito_stack_name = cognito_stack_name
        # check if Cognito stack name was passed as a stack parameter instead
        # use default value if nothing else works
        if cognito_stack_name == "":
            this.cognito_stack_name = "apigw - samples - cognito - shared"
        
        cognito_stack_name_prefix = this.cognito_stack_name.replace('-', '')
        
        #create LambdaAuthorizer Function
        api_lambda_authorizer = _lambda.Function(this,'AuthorizerFunction-',
            handler='authorizer.lambda_handler',
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("src/api",
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_9.bundling_image,
                    command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            environment={
                'USER_POOL_ID': cdk.Fn.import_value(
                    cognito_stack_name_prefix + 'UserPool'),
                'APPLICATION_CLIENT_ID': cdk.Fn.import_value(
                    cognito_stack_name_prefix + 'UserPoolClient'),
                'ADMIN_GROUP_NAME': cdk.Fn.import_value(
                    cognito_stack_name_prefix + 'UserPoolAdminGroupName'),
                'AWS_XRAY_TRACING_NAME': this.stack_name,
                'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'
                }

        )

        return api_lambda_authorizer

    @staticmethod
    def create_msg_store_DDB_table(this)->None:
        sqs_msg_store_table = ddb.Table(this, 'job-reqeust-store-',
                                    partition_key=ddb.Attribute(name='jobRequestId', type=ddb.AttributeType.STRING)                                    
                                    )
        sqs_msg_store_table.add_global_secondary_index(index_name='eventSourceGSI',
                                                   partition_key=ddb.Attribute(name='eventSource',
                                                                               type=ddb.AttributeType.STRING),
                                                   projection_type=ddb.ProjectionType.ALL
                                                   )

        return sqs_msg_store_table

    def create_rest_api_base (this, authorizer)->None:
        #Create REST API
        api_log_group = logs.LogGroup(this, 'ApiLogs', retention=logs.RetentionDays.ONE_MONTH)
        #'format': '{ "requestId":"$context.requestId", "ip": "$context.identity.sourceIp", "requestTime":"$context.requestTime", "httpMethod":"$context.httpMethod","routeKey":"$context.routeKey", "status":"$context.status","protocol":"$context.protocol", "integrationStatus": $context.integrationStatus, "integrationLatency": $context.integrationLatency, "responseLength":"$context.responseLength" }'

        log_format= {
                "request_id": apigw.AccessLogField.context_request_id(),
                "ip": apigw.AccessLogField.context_identity_source_ip(),
                "httpMethod": apigw.AccessLogField.context_http_method(),
                "requestTime":apigw.AccessLogField.context_request_time(),
                #"routeKey":apigw.AccessLogField.context_route_key(),
                "status":apigw.AccessLogField.context_status(),
                "protocol":apigw.AccessLogField.context_protocol(),
                "integrationStatus":apigw.AccessLogField.context_integration_status(),
                "integrationLatency":apigw.AccessLogField.context_integration_latency,
                "responseLength":apigw.AccessLogField.context_response_length()
                }

        base_api = apigw.RestApi(this, 'ApiGW',rest_api_name='JobRequestRestAPI-'+this.stack_name,
                            default_method_options={"authorizer": authorizer}, 
                            cloud_watch_role=True,
                            deploy_options=apigw.StageOptions(
                                access_log_destination=apigw.LogGroupLogDestination(api_log_group),
                                #access_log_format=apigw.AccessLogFormat.custom(f"{apigw.AccessLogField.context_request_id()} {apigw.AccessLogField.context_error_message()} {apigw.AccessLogField.contextErrorMessageString()}")
                                access_log_format=apigw.AccessLogFormat.custom(str(log_format))

                            )
        )
        base_api.root.add_method("ANY")

        return base_api

    def create_rest_api_submit_job(this, base_api,rest_api_role, job_request_queue)->None :
        
        #Create a resource named "example" on the base API
        api_resource = base_api.root.add_resource('submit-job-request')

        #Create API Integration Response object: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_apigateway/IntegrationResponse.html
        integration_response = apigw.IntegrationResponse(
            status_code="200",
            response_templates={"application/json": ""},

        )

        #Create API Integration Options object: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_apigateway/IntegrationOptions.html

        api_integration_options = apigw.IntegrationOptions(
            credentials_role=rest_api_role,
            integration_responses=[integration_response],
            request_templates={"application/json": "Action=SendMessage&MessageBody=$input.body"},
            passthrough_behavior=apigw.PassthroughBehavior.NEVER,
            request_parameters={"integration.request.header.Content-Type": "'application/x-www-form-urlencoded'"},
        )

        #Create AWS Integration Object for SQS: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_apigateway/AwsIntegration.html
        api_resource_sqs_integration = apigw.AwsIntegration(
            service="sqs",
            integration_http_method="POST",
            path="{}/{}".format(Aws.ACCOUNT_ID, job_request_queue.queue_name),
            options=api_integration_options
        )

        #Create a Method Response Object: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_apigateway/MethodResponse.html
        method_response = apigw.MethodResponse(status_code="200")

        #Add the API GW Integration to the "example" API GW Resource
        api_resource.add_method(
            "POST",
            api_resource_sqs_integration,
            method_responses=[method_response]
        )
        return api_resource

    def create_sqs_processor_function(this, sqs_msg_store_ddb_tbl, job_request_queue, batch_simulator_function)->None :
        #Creating Lambda function that will be triggered by the SQS Queue
        sqs_processor_lambda = _lambda.Function(this,'SQSMessageProcessorFunction',
            handler='sqs_processor.lambda_handler',
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('src/api'),
            timeout=cdk.Duration.seconds(180),            
            environment={
                        'BATCH_SIMULATOR_FUNCTION_NAME': batch_simulator_function.function_arn,
                        'SQS_MESSAGE_STORE_TABLE_NAME':sqs_msg_store_ddb_tbl.table_name
                        }

        )

        #Create an SQS event source for Lambda
        sqs_event_source = lambda_event_source.SqsEventSource(job_request_queue)

        #Add SQS event source to the Lambda function
        sqs_processor_lambda.add_event_source(sqs_event_source)
        return sqs_processor_lambda
    
    def create_batch_simulator_function(this, s3_bucket)->None :
        #Creating batch simulator Lambda function that will create weather data and store in S3 Bucket
        batch_simulator_lambda = _lambda.Function(this,'BatchSimulatorFunction',
            handler='batch_simulator.lambda_handler',
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('src/api'),
            timeout=cdk.Duration.seconds(120),
            environment={
                        'BATCH_SIMULATOR_BUCKET_NAME': s3_bucket.bucket_name,
                        }
        )
        
        return batch_simulator_lambda

    def create_job_output_payload_s3 (this)-> None:
        #Creating get job status Lambda function that will provide latest status of Job and S3 presigned url for weather data
        job_output_payload_s3 = s3.Bucket(
            this,
            "job-payload-output-bucket"+ this.stack_name,
            bucket_name = "job-payload-output-bucket"+ this.stack_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        return  job_output_payload_s3

    def create_get_job_status_function(this, sqs_msg_store_ddb_tbl)->None :
        get_job_status_lambda = _lambda.Function(this,'GetJobStatusFunction',
            handler='get_job_status.lambda_handler',
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('src/api'),
            environment={
                        'SQS_MESSAGE_STORE_TABLE_NAME':sqs_msg_store_ddb_tbl.table_name
                        }
        )
        
        return get_job_status_lambda
    
    def create_cw_dashboard(this,base_api, sqs_processor_lambda,  get_job_status_function, batch_simulator_function, sqs_msg_store_ddb_tbl)->None:
        application_dashboard = cwl.Dashboard(this, 'ApplicationDashboard',
                                              dashboard_name=this.stack_name + '-Dashboard')
        application_dashboard.add_widgets(
            cwl.GraphWidget(title='API Gateway',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='DataProcessed',
                                    dimensions_map={'ApiId': base_api.rest_api_id},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='IntegrationLatency',
                                    dimensions_map={'ApiId': base_api.rest_api_id},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='Latency',
                                    dimensions_map={'ApiId': base_api.rest_api_id},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                            ],
                            right=[
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='4xx',
                                    dimensions_map={'ApiId': base_api.rest_api_id},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='5xx',
                                    dimensions_map={'ApiId': base_api.rest_api_id},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/ApiGateway',
                                    metric_name='Count',
                                    dimensions_map={'ApiId': base_api.rest_api_id},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                            ]
                            )
        )
        application_dashboard.add_widgets(
            cwl.GraphWidget(title='SQS Message Processor Lambda',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Invocations',
                                    dimensions_map={
                                        'FunctionName': sqs_processor_lambda.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Errors',
                                    dimensions_map={
                                        'FunctionName': sqs_processor_lambda.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Throttles',
                                    dimensions_map={
                                        'FunctionName': sqs_processor_lambda.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Duration',
                                    dimensions_map={
                                        'FunctionName': sqs_processor_lambda.function_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='ConcurrentExecutions',
                                    dimensions_map={
                                        'FunctionName': sqs_processor_lambda.function_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                )
                            ]
                            ),
            cwl.GraphWidget(title='Batch Simulator Lambda',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Invocations',
                                    dimensions_map={
                                        'FunctionName': batch_simulator_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Errors',
                                    dimensions_map={
                                        'FunctionName': batch_simulator_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Throttles',
                                    dimensions_map={
                                        'FunctionName': batch_simulator_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Duration',
                                    dimensions_map={
                                        'FunctionName': batch_simulator_function.function_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='ConcurrentExecutions',
                                    dimensions_map={
                                        'FunctionName': batch_simulator_function.function_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                )
                            ]
                            ),
            cwl.GraphWidget(title='Get Job Status Lambda',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Invocations',
                                    dimensions_map={
                                        'FunctionName': get_job_status_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Errors',
                                    dimensions_map={
                                        'FunctionName': get_job_status_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Throttles',
                                    dimensions_map={
                                        'FunctionName': get_job_status_function.function_name},
                                    statistic='Sum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='Duration',
                                    dimensions_map={
                                        'FunctionName': get_job_status_function.function_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/Lambda',
                                    metric_name='ConcurrentExecutions',
                                    dimensions_map={
                                        'FunctionName': get_job_status_function.function_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                )
                            ]
                            )
        )
        application_dashboard.add_widgets(
            cwl.GraphWidget(title='DynamoDB - SQS Message Store',
                            width=6,
                            height=6,
                            left=[
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ConsumedReadCapacityUnits',
                                    dimensions_map={
                                        'TableName': sqs_msg_store_ddb_tbl.table_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ConsumedWriteCapacityUnits',
                                    dimensions_map={
                                        'TableName': sqs_msg_store_ddb_tbl.table_name},
                                    statistic='Maximum',
                                    period=cdk.Duration.minutes(1)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ProvisionedReadCapacityUnits',
                                    dimensions_map={
                                        'TableName': sqs_msg_store_ddb_tbl.table_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(5)
                                ),
                                cwl.Metric(
                                    namespace='AWS/DynamoDB',
                                    metric_name='ProvisionedWriteCapacityUnits',
                                    dimensions_map={
                                        'TableName': sqs_msg_store_ddb_tbl.table_name},
                                    statistic='Average',
                                    period=cdk.Duration.minutes(5)
                                )
                            ]
                            ),
        )
