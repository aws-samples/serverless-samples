# API Monetization — Usage Reports from Access Logs

This module extends the [API Gateway Log Analytics](../README.md) solution to generate per-customer usage reports that can serve as the basis for invoicing. It reads the same access logs already collected in S3 and applies configurable pricing to produce reports showing what each API consumer owes (or, for subscription customers, whether the API owner is profitable).

> [!NOTE]
> This module requires the `apigw-log-analytic` stack to be deployed first. It uses the same S3 bucket and Glue database created by that stack.

## Overview

The `apigw-log-analytic` solution already captures every API request: API Gateway → Firehose → S3, enriched with the customer's API key name and usage plan. This module queries that data with Athena, applies a pricing plan, generates per-customer reports, and compiles a consolidated billing file (JSON + CSV) ready for download or import into billing systems.

```
Access logs in S3 (from apigw-log-analytic stack)
        │
        ▼
  Step Functions workflow (scheduled monthly or ad-hoc)
        │
        ├── 1. Query Athena: aggregate usage per customer
        │
        ├── 2. For each customer:
        │       ├── Look up their pricing plan in DynamoDB
        │       ├── Calculate charges based on pricing model
        │       └── Store individual report in DynamoDB + S3
        │
        └── 3. Compile consolidated report
                ├── JSON summary with all customers and line items
                └── CSV file for spreadsheet/billing system import
```

The workflow runs automatically on the 1st of each month (configurable via the `ReportSchedule` parameter) and can also be triggered ad-hoc for any billing period. The final step produces downloadable report files in S3 and returns presigned URLs in the execution output.

The connection between customers and pricing plans is through the API Gateway usage plan name. The enrichment Lambda stamps each log with the usage plan name, and each pricing plan has a `usagePlanName` field that maps to it. At report time, the customer's usage plan is matched to a pricing plan in DynamoDB.

## Pricing Models

Each pricing plan has a `model` field that determines how charges are calculated.

### Consumption (pay-per-use)

Flat rate — every request costs the same.

```json
{ "planId": "payg", "model": "consumption", "perRequestRate": 0.001, "perGbRate": 0.10 }
```

Report output: `250,000 requests × $0.001 = $250.00`

### Tiered

Rate drops at higher volumes.

```json
{
  "planId": "tiered", "model": "tiered",
  "tiers": [
    { "upTo": 10000, "rate": 0.002 },
    { "upTo": 100000, "rate": 0.001 },
    { "upTo": 999999999, "rate": 0.0005 }
  ]
}
```

Report output: first 10K at $0.002, next 90K at $0.001, rest at $0.0005.

### Subscription (profitability view)

The customer pays a fixed monthly fee. The report doesn't bill them — instead it shows the API owner whether they're making money by comparing the subscription fee against estimated cost to serve.

```json
{ "planId": "pro", "model": "subscription", "baseFee": 99.00, "costPerRequest": 0.0005 }
```

Report output includes a profitability section:
```json
{
  "profitability": {
    "subscriptionFee": 99.00,
    "estimatedCostToServe": 45.00,
    "margin": 54.00,
    "profitable": true
  }
}
```

### Freemium

Free up to a quota, then overage charges apply.

```json
{ "planId": "free", "model": "freemium", "freeQuota": 10000, "overageRate": 0.003 }
```

Report output: `10,000 free + 5,000 overage × $0.003 = $15.00`

## Prerequisites

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) (AWS SAM) installed
* Python 3.13+
* The [apigw-log-analytic](../README.md) stack deployed

> [!NOTE]
> Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Deployment

After deploying the `apigw-log-analytic` stack, navigate to the monetization directory:

```bash
cd monetization
```

Build and deploy:

```bash
sam build
sam deploy --guided
```

During the prompts:
* Enter a stack name
* Enter the desired AWS Region (must match the region where `apigw-log-analytic` is deployed)
* **ProjectName** — Must match the ProjectName from the `apigw-log-analytic` stack
* **AccessLogsBucketName** — S3 bucket containing API Gateway access logs (from stack output)
* **GlueDatabaseName** — Glue database name (typically same as ProjectName)
* **ReportSchedule** — When to generate reports (default: 1st of each month at 2am UTC)
* Allow SAM CLI to create IAM roles with the required permissions

Once you have run `sam deploy --guided` mode once and saved arguments to a configuration file (samconfig.toml), you can use `sam deploy` in future to use these defaults.

Copy the API URL from the stack outputs for use in the testing section.

### Load sample pricing plans

Optionally, seed the DynamoDB table with sample pricing plans covering all four models:

```bash
python3 sample-plans/seed_plans.py <ProjectName>-pricing-plans --region <region>
```

## Testing

To test end-to-end, you need API Gateway access logs flowing into S3 with API key data. Follow these steps in order.

### 1. Set the API URL

```bash
API_URL=<ApiUrl from stack output>
```

### 2. Verify pricing plans are loaded

If you ran the seed script during deployment:

```bash
curl "$API_URL/pricing"
```

You should see four plans (payg, tiered, pro-subscription, free). If not, load them:

```bash
python3 sample-plans/seed_plans.py <ProjectName>-pricing-plans --region <region>
```

### 3. Ensure access logs are flowing

If you don't already have an API Gateway configured with access logging:

1. Create a REST API in the API Gateway console (or use the [Example API](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-api-from-example.html))
2. Create a **Usage Plan** (e.g., name it `PayAsYouGoPlan` to match the sample pricing plan)
3. Associate the usage plan with your API stage
4. Create an **API Key** and associate it with the usage plan
5. Configure **Access Logging** on the stage via the API Gateway console:
   - Go to **API Gateway** → your API → **Stages** → select your stage
   - Click the **Logs and tracing** tab
   - Enable **Access logging**
   - Set the **Destination ARN** to the Firehose delivery stream ARN from the `apigw-log-analytic` stack output (`DeliveryStream`)
   - Paste the following as the **Log format**:
     ```
     {"apiId":"$context.apiId","stage":"$context.stage","requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","routeKey":"$context.routeKey","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength","accountId":"$context.accountId","domainName":"$context.domainName","domainPrefix":"$context.domainPrefix","errorMessage":"$context.error.message","errorResponseType":"$context.error.responseType","identityAccountId":"$context.identity.accountId","identityApiKeyId":"$context.identity.apiKeyId","identityCaller":"$context.identity.caller","identityUser":"$context.identity.user","identityUserAgent":"$context.identity.userAgent","identityUserArn":"$context.identity.userArn","path":"$context.path","resourcePath":"$context.resourcePath","integrationLatency":"$context.integration.latency","responseLatency":"$context.responseLatency"}
     ```
   - Click **Save**
6. Make API requests using the API key:
   ```bash
   for i in {1..50}; do
     curl -s -H "x-api-key: <your-api-key-value>" "https://<api-id>.execute-api.<region>.amazonaws.com/<stage>/your-resource" > /dev/null
   done
   ```
7. Wait ~15 minutes for Firehose to flush to S3 (5 min buffer) and the Glue crawler to index the data (runs every 10 min). Verify logs landed in S3:
   ```bash
   aws s3 ls s3://<AccessLogsBucket>/logs/ --recursive --region <region>
   ```

> **Important:** The `usagePlanName` in your pricing plan must match the actual API Gateway usage plan name. If you used the sample plans, either name your usage plan `PayAsYouGoPlan`, or update the pricing plan:
> ```bash
> curl -X PUT "$API_URL/pricing/payg" -H "Content-Type: application/json" \
>   -d '{"model":"consumption", "usagePlanName":"<YourActualUsagePlanName>", "perRequestRate":0.001, "perGbRate":0.10}'
> ```

### 4. Trigger report generation

```bash
aws stepfunctions start-execution \
  --state-machine-arn <ReportWorkflowArn from stack output> \
  --input '{"billingPeriod": "2025-05"}' \
  --region <region>
```

### 5. Verify the results

Check the execution status:

```bash
aws stepfunctions describe-execution \
  --execution-arn <execution-arn-from-above> \
  --region <region>
```

Once `"status": "SUCCEEDED"`, the output contains download URLs for the consolidated report (JSON + CSV).

List generated reports via the API:

```bash
curl "$API_URL/reports"
```

Get a specific report (includes a presigned S3 download URL):

```bash
curl "$API_URL/reports/<reportId>"
```

Expected output for a customer on the consumption plan with 50 requests:

```json
{
  "reportId": "RPT-2025-05-test-customer-1-a1b2c3d4",
  "customerId": "test-customer-1",
  "pricingModel": "consumption",
  "estimatedTotal": 0.05,
  "lineItems": [
    { "description": "50 API requests @ $0.001/req", "quantity": 50, "unitPrice": 0.001, "amount": 0.05 }
  ]
}
```

### Pricing plans API reference

```bash
# Create a plan
curl -X POST "$API_URL/pricing" -H "Content-Type: application/json" \
  -d '{"planId":"custom", "model":"consumption", "usagePlanName":"MyPlan", "perRequestRate":0.002}'

# Get a plan
curl "$API_URL/pricing/custom"

# Update a plan
curl -X PUT "$API_URL/pricing/custom" -H "Content-Type: application/json" \
  -d '{"model":"consumption", "usagePlanName":"MyPlan", "perRequestRate":0.003}'

# Delete a plan
curl -X DELETE "$API_URL/pricing/custom"
```

## Project Structure

```
monetization/
├── template.yaml                  # SAM template
├── statemachine/
│   └── billing.asl.json           # Step Functions workflow
├── src/
│   ├── query_usage.py             # Athena query for per-customer usage
│   ├── generate_report.py         # Applies pricing and creates per-customer report
│   ├── compile_report.py          # Compiles consolidated JSON + CSV report files
│   ├── manage_pricing.py          # Pricing plans CRUD API
│   └── get_reports.py             # Reports retrieval API
├── sample-plans/
│   └── seed_plans.py              # Load sample plans into DynamoDB
└── README.md
```

## Cleanup

Delete the stack. Note that the reports S3 bucket is retained for reference and may need to be manually deleted.

```bash
sam delete
```

Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
