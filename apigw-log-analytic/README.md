# Logging API Gateway access logs, analyzing and visualizing them using Amazon QuickSight

[Amazon API Gateway](https://aws.amazon.com/api-gateway/) is a fully managed service that makes it easy for developers to create, publish, maintain, monitor, and secure APIs at any scale. APIs act as the 'front door' for applications to access data, business logic, or functionality from your backend services. API Gateway can produce detailed access logs to show who has accessed the API. When using usage plans, a customer identifier is included in the log records. API developers can use these access logs to identify popular routes, errors, authentication methods, users reaching quota limits, and gain deeper insights into API usage.

You can use these logs to populate a business intelligence service, such as [Amazon QuickSight](https://aws.amazon.com/quicksight/), to analyze and report on usage patterns across your APIs and customers.

In this repo, I will show how to visualize and analyze API Gateway access logs using [Amazon QuickSight dahboard](https://docs.aws.amazon.com/quicksight/latest/user/example-create-a-dashboard.html). This pre-built dashboard enables you to analyze API usage by visualizing the following components:

* 30 days of API usage by domain
* API routes showing popular API paths
* API breakdown by status code
* 400 errors (quota exceeded, unauthorized, and invalid-signature) requests
* 500 errors
* API usage by usage plan and API key
* Users hitting quota limits
* API calls by user agent
* Authentication methods
* Cognito-based access control
* IAM authorization
* Latency metrics for APIs and the Lambda authorizer
* Filter visualizations and reports by date, domain, status, usage plan, IP, and users (IAM or Cognito users)

As we are using QuickSight for the visualization part, you have the flexibility to customize these tables and graphs based on your business use case. You can also set up [Amazon QuickSight Paginated Reports](https://aws.amazon.com/quicksight/paginated-reports/) and share reports and data exports from a single, fully managed, cloud-based business intelligence (BI) solution. API owners and product managers can receive daily or weekly reports on your API consumption.

**Dashboard overview**

![dashboard overview](./assets/apigw-log-analytic-dashboard-overview.jpg)


## Solution Overview 

The integration works by forwarding API Gateway access logs from your API Gateway to Amazon S3 bucket via [Amazon Data Firehose](https://www.google.com/search?client=firefox-b-1-d&q=Amazon+Kinesis+Data+Firehose). This solution uses the following AWS services to provide near real-time logging analytics:

* Amazon S3 bucket ensures durable and secure storage.
* Amazon Data Firehose to deliver logs into an S3 bucket.
* AWS Lambda function for log enrichment.
* AWS Glue crawler to provide fresher data to QuickSight.
* QuickSight for analytics and visualization.

  ![Architecture diagram](./assets/apigw-log-analytic-solution-overview.jpg)

## Streamlining API Access Logs
API access logs are streamed in near real-time from API Gateway to Firehose. Firehose buffers these records, enriching them with information from the API usage plans. It then writes batches of enhanced records to an Amazon S3 bucket, ensuring durable and secure storage. To enrich the access logs, an AWS Lambda function is used. The Lambda function retrieves API Gateway usage plan details and loads them into memory. During each invocation, it processes each access log record from Firehose stream by decoding it from a base64-encoded binary. The record is then enriched with the usage plan name and customer name before being re-encoded to base64 binary and returned to the Firehose stream.

## Indexing Access Logs
Metadata for the API access logs is stored in an [AWS Glue Data Catalog](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html), which QuickSight uses for querying. An AWS Glue crawler identifies and indexes newly written access logs. You can adjust the frequency of the crawler to ensure fresher data is available in QuickSight by updating the DataRefreshFrequency parameter of the SAM template when deploying the solution. The default data refresh frequency is every 10 minutes (cron(0/10 * * * ? *)).

## Visualizing Data
QuickSight is configured to use the S3 location of the access logs as a data source, enabling comprehensive analysis and visualization.

## Pre-requisites 

If you have not activated QuickSight in your AWS account, follow the steps below. Otherwise, you can skip to step 2.

1. Create a QuickSight Account.
    1. Navigate to QuickSight service from the AWS Management console.
    2. Click **Sign up for QuickSight**.
    3. Enter Email and account name.

  ![Pre-requisites1](./assets/apigw-log-analytic-prerequisite1.jpg)

2. Once QuickSight account setup is complete, from the QuickSight console, select your username to open the menu. Select “Manage QuickSight”.
3. On the left menu, select “Manage Groups”.
4. Select the “NEW GROUP” button and name the group in the format “<projectName>-Admins” (It is case sensitive). Select “CREATE.” For example, apiaccesslogs-Admins.
5. Add yourself as an administrator to the dashboard by selecting the newly created group name, then click “ADD USER.”
6. Copy the project name without '-Admins' as this is required for the project name parameters in the SAM template. It needs to be the exact same name for deployment.

 ![Pre-requisites1](./assets/apigw-log-analytic-prerequisite2.jpg)

## Implementation

Note: This solution supports the [REST API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html).

This solution won’t create an API Gateway in your AWS account and assumes you have an API endpoint. If you do not, follow [this tutorial](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-api-from-example.html) to create one.

Deploy an AWS SAM template into your account. This template creates all components of the analytics pipeline, including an Amazon S3 bucket, Firehose, Lambda functions, AWS Glue, QuickSight dashboards and visuals, using Infrastructure as Code (IaC).

Once deployment is complete, configure existing API Gateway to deliver access logs to the deployed Firehose stream.

## Launch the AWS SAM Template

From your local terminal, run the following commands:

```
git clone https://github.com/aws-samples/apigw-log-analytic.git
cd apigw-log-analytic
sam build
sam deploy -g 
```

Enter the following parameters for deployment:

- Stack Name: Use if for stack name. For example apgwaccesslogs.
- ProjectName: Use the project name without '-Admins'. Ensure it matches the one created in the Prerequisites section 6.
- DataRefreshFrequency: You can leave as default (every 10 minutes) or customize it based on your requirement.

![deployment](./assets/apigw-log-analytic-deployment1.jpg)
 
![deployment](./assets/apigw-log-analytic-deployment2.jpg)

Wait a couple of minutes for the deployment to complete. Once the stack has been successfully created, copy the Amazon Resource Names (ARNs) of the Firehose stream and S3 bucket from the output. These resource ARNs are required for the next steps in configuring API Gateway access logging.

![deployment](./assets/apigw-log-analytic-deployment3.jpg)

## Authorize Amazon QuickSight to access your Amazon S3 bucket

1. Followthe instructions to authorize Amazon QuickSight to access API Gateway S3 access logs.
2. Select the S3 access logs bucket created and Finish and Save.

![Pre-requisites1](./assets/apigw-log-analytic-qs-security.jpg)

![Pre-requisites1](./assets/apigw-log-analytic-s3-permissions.jpg)


## Configure API Gateway to stream access logs to this Data Firehose stream

1. You can now configure API Gateway to stream access logs to this Firehose delivery stream. [Follow these instructions](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-logging-to-kinesis.html#set-up-kinesis-access-logging-using-console) to turn on access logging on your API stages using the ARN of the Firehose delivery stream created via SAM template.
2. Under Log Format, choose the fields to include in the access logs in JSON format. Find [examples in the API Gateway documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html#apigateway-cloudwatch-log-formats) as well as the [full set of available fields in the $context variable](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-mapping-template-reference.html#context-variable-reference). The below fields and mapped names are required for the analysis.

```
{"apiId":"$context.apiId","stage":"$context.stage","requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","routeKey":"$context.routeKey","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength","accountId":"$context.accountId","authorizerClaimsProperty":"$context.authorizer.claims.property","authorizerPrincipalId":"$context.authorizer.principalId","authorizerProperty":"$context.authorizer.property","domainName":"$context.domainName","domainPrefix":"$context.domainPrefix","errorMessage":"$context.error.message","errorResponseType":"$context.error.responseType","identityAccountId":"$context.identity.accountId","identityApiKeyId":"$context.identity.apiKeyId","identityCaller":"$context.identity.caller","identityCognitoAuthenticationProvider":"$context.identity.cognitoAuthenticationProvider","identityCognitoAuthenticationType":"$context.identity.cognitoAuthenticationType","identityCognitoIdentityId":"$context.identity.cognitoIdentityId","identityCognitoIdentityPoolId":"$context.identity.cognitoIdentityPoolId","identityPrincipalOrgId":"$context.identity.principalOrgId","identityUser":"$context.identity.user","identityUserAgent":"$context.identity.userAgent","identityUserArn":"$context.identity.userArn","path":"$context.path","resourcePath":"$context.resourcePath","wafResponseCode":"$context.wafResponseCode","webaclArn":"$context.webaclArn","sub":"$context.authorizer.claims.sub","clientId":"$context.authorizer.claims.iss","aud":"$context.authorizer.claims.aud","authorizeError":"$context.authorize.error","authorizeLatency":"$context.authorize.latency","authorizeStatus":"$context.authorize.status","authorizerError":"$context.authorizer.error","authorizerIntegrationLatency":"$context.authorizer.integrationLatency","authorizerIntegrationStatus":"$context.authorizer.integrationStatus","authorizerLatency":"$context.authorizer.latency","authorizerStatus":"$context.authorizer.status","integrationLatency":"$context.integration.latency","responseLatency":"$context.responseLatency"}
```
![log format](./assets/apigw-log-analytic-access-logging-setup.jpg)


## Data Visualization

Once you configure API Gateway access logs, it takes a few minutes for the logs to appear in the QuickSight dashboard. This pre-built dashboard allows you to analyze API usage by visualizing components such as 30 days of API usage by domain, popular API paths, 400 errors (quota exceeded, unauthorized, and invalid-signature) requests, users hitting quota limits, and Cognito-based and IAM authorization. Additionally, you can filter visualizations and reports by date, customer, status, usage plan, IP, and users (IAM or Cognito users). You can also customize these visuals or create new ones for your business use case, as additional context fields have been included in the API access logs.

**Dashboard overview**

![dashboard overview](./assets/apigw-log-analytic-dashboard-overview.jpg)

This pre-built dashboard allows you to analyze API usage by providing visualizations of the following components:

**Congnito based access control**

If you are using [Amazon Cognito](https://aws.amazon.com/pm/cognito/?gclid=CjwKCAjw74e1BhBnEiwAbqOAjNsHPd0SoVxdGF33x27NozfK-9PWWQ2_1x62VdHIAajb2B9XUcjCzhoC8hYQAvD_BwE&trk=f5fef02c-2926-48d3-898a-b4d668742a20&sc_channel=ps&ef_id=CjwKCAjw74e1BhBnEiwAbqOAjNsHPd0SoVxdGF33x27NozfK-9PWWQ2_1x62VdHIAajb2B9XUcjCzhoC8hYQAvD_BwE:G:s&s_kwcid=AL!4422!3!651737511575!e!!g!!amazon%20cognito!19845796024!146736269189) to control access to REST APIs, this visual can help you understand which users are interacting with your APIs.

![dashboard overview](./assets/apigw-log-analytic-cognito.jpg)

**400 errors (quota exceeded, unauthorized, and invalid-signature) requests**

This visual provides insights into 4xx errors in your API requests, focusing on quota exceeded, unauthorized, and invalid signature errors. You can identify trends and patterns affecting your API's performance and reliability. This breakdown helps pinpoint root causes, enabling targeted improvements, enhanced security measures, and optimized quota management for a seamless and secure API experience.

![dashboard overview](./assets/apigw-log-analytic-400-errors.jpg)

**API by usage plan**

[A usage plan](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html#api-gateway-api-usage-plans-overview) specifies who can access one or more deployed API stages and methods. This visual provides an overview of API usage by usage plan, domain, and path, highlighting request counts and their utilization across different plans.

![dashboard overview](./assets/apigw-log-analytic-usageplan.jpg)

**API Latency Metrics**

This visual shows latency metrics such as response latency, integration latency, and Lambda authorizer latency. It helps you see how each API performs and where you can make improvements.

![Latency metrics](./assets/apigw-log-analytic-latency.jpg)

## How to open the dashboard

1. Navigate to the QuickSight console.
2. Select Dashboard and open the deployed QuickSight dashboard.

![dashboard overview](./assets/apigw-log-analytic-dashboard-navigation.jpg)

## Cleaning Up 

The SAM delete command deletes an AWS SAM application by deleting the AWS CloudFormation stack and the artifacts.

Note - API Gateway access logs are retained in the S3 bucket for future reference. You may need to manually delete the bucket if necessary.

```
cd apigw-log-analytic
sam delete
```

## Conclusion

In this repo, I walked you through how API Gateway's detailed access logs provide insights into API usage. These logs include customer identifiers with usage plans, helping developers identify popular routes, errors, authentication methods, and users reaching quota limits. By using these logs, you can populate QuickSight to analyze and report on API usage patterns across domains and customer segments. 

You can customize this dashboard by creating additional visuals and tables based on your business use case. Additionally, you can customize the Lambda enrichment logic, for example, to add geo information for IP addresses and create geographic dashboards within QuickSight to identify geographically separated users.
