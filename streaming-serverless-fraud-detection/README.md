# Real-time transaction fraud detection/prevention using Serverless and Amazon Fraud Detector

This example demonstrates a serverless approach to detect online transaction fraud in near real-time. It shows how detection can be plugged into various data streaming and event- driven architectures, depending on the outcome to be achieved and actions to be taken to prevent fraud - alert the customer/user about the fraud, flag the transaction for additional review, etc.

This sample implements three architectures:
 - [Streaming data inspection and fraud detection/prevention](#streaming-data-inspection-and-fraud-detectionprevention) - using Amazon Kinesis Data Stream, AWS Lambda, AWS Step Functions, and Amazon Fraud Detector
 - [Streaming data enrichment for fraud detection/prevention](#streaming-data-enrichment) - using Amazon Kinesis Data Firehose, Lambda, and Amazon Fraud Detector
 - [Event data inspection and fraud detection/prevention](#event-data-inspection) - using Amazon EventBridge, Step Functions, and Amazon Fraud Detector

## Streaming data inspection and fraud detection/prevention

### Overview
This architecture uses Lambda and Step Functions to enable real-time Kinesis Data Stream data inspection and fraud detection/prevention using Amazon Fraud Detector. The same architecture would apply in case you use Amazon MSK as a data streaming service. This pattern can be useful for real-time fraud detection, notification and potential prevention. Example use cases for this could be payment-processing or high volume account creation.

![Architecture](./assets/architecture_stream_consumer.png)

The flow of the events is as follows. 

1. Ingest the financial transactions into the Kinesis Data streams. The source of the data could be a system that generates these transactions - for example, e-commerce, banking, etc. 
2. The Lambda function receives the transactions in batches  
3. The Lambda function starts Step Functions workflow execution for the batch: 
    - For each transaction in the batch: 
        * Persist the transaction in an Amazon DynamoDB table 
        * Call the Amazon Fraud Detector API using GetEventPrediction action
            - The API returns either of these 3 results - “approve”, “block” or “investigate” 
        * Update transaction in the DynamoDB table with fraud prediction results
        * Based on the results - 
            - send a notification using Amazon Simple Notification Service (SNS) in case of “block” or “investigate” 
            - process transaction further in case of “approve”

This approach allows you to react to the potentially fraudulent transactions in real-time as we store each transaction in a database and inspect it before processing further. In actual implementation, you may replace the notification step for additional review with an action that is specific to your business process–for example, inspect transaction using some other fraud detection model, manual review, etc.

### Deployment
1. The Amazon Fraud Detector model and the detector should be pre-built based on the past data. Follow [this blog post](https://aws.amazon.com/blogs/machine-learning/detect-online-transaction-fraud-with-new-amazon-fraud-detector-features/) for more detailed instructions.
2. Clone this repo, navigate to the directory streaming-serverless-fraud-detection
3. Run the following commands:
```bash
cd kinesis-data-stream-detection
sam build
sam deploy --guided --stack-name kinesis-data-stream-fraud-detection
```

### Try it out
To try this solution, we need to send data to the Kinesis Data Stream. You can use [Kinesis Data Generator](https://github.com/awslabs/amazon-kinesis-data-generator) for that. Once you deployed the Data Generator and logged in, select Kinesis Data Stream that matches the one in the Outputs section of your deployed fraud detection sample stack. You can use the following command to get stack details (check Outputs for the stream name):

```bash
aws cloudformation describe-stacks --stack-name kinesis-data-stream-fraud-detection
```

You can use the following template for transaction record generation:

```code=json
    {
        "transaction_id":"{{random.number({"min":10000, "max":100000})}}",
        "transaction_timestamp":"{{date.now("YYYY-MM-DDTHH:mm:ss")}}Z",
        "customer_email": "{{random.arrayElement(["admin@example.com","user@example.com","employee@example.com","customer@example.com"])}}",
        "order_price": "{{random.number({"min":10, "max":1000})}}",
        "product_category": "{{random.arrayElement(["kitchen","garden","groceries","leisure"])}}",
        "ip_address": "{{internet.ip}}",
        "card_bin": "{{random.number(
            {
                "min":1,
                "max":99999
            }
        )}}"
    }
```
**Note:** 
*Keep in mind Amazon Fraud Detector quotas for your account and use appropriate batch sizes (for example, send 10 records at a time).* 

Stop record generation after you send a few batches to the Kinesis Data Stream. You can check Step Functions execution logs following the link in the stack outputs. Note that only errors are logged and that execution data is not included. 

### Cleaning Up
To avoid incurring further charges when you do not need this process anymore, run the following command:
```bash
sam delete --stack-name kinesis-data-stream-fraud-detection 
```

## Streaming data enrichment for fraud detection/prevention

### Overview
This architecture uses Lambda to enable real-time Kinesis Data Firehose data enrichment using Amazon Fraud Detector and [Kinesis Data Firehose Data Transformation](https://docs.aws.amazon.com/firehose/latest/dev/data-transformation.html). This sample does not implement fraud detection/prevention steps. We deliver enriched data to the Amazon S3 bucket, downstream services that consume the data can use fraud detection results in their business logics, and act accordingly.

![Architecture](./assets/architecture_stream_enrichment.png)

Note, that you could use [EventBridge Pipes](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html#pipes-enrichment) with an Enrichment step that uses Lambda to implement a similar approach.

The flow of the events is as follows. 

1. We ingest the financial transactions into Kinesis Data Firehose. The source of the data could be a system that generates these transactions - for example, e-commerce, banking, etc. 
2. Lambda function receives the transactions in batches and enriches them 
    - For each transaction in the batch: 
        * Calls the Amazon Fraud Detector API using GetEventPrediction action
        * The API returns either of these 3 results - “approve”, “block” or “investigate” 
        * Update transaction data by adding fraud detection results
3. Lambda function returns batch with the updated transactions to the Kinesis Data Firehose
4. Kinesis Data Firehose delivers data to the destination (in our case, the Amazon S3 bucket)

As a result, we have data in the Amazon S3 bucket that includes not only original data but also the Amazon Fraud Detector response as a metadata for each of the transactions. You can use this metadata in your data analytics solutions, machine learning model training tasks, or visualizations/dashboards that consume transaction data.

### Deployment
1. The Fraud Detector model and the detector should be pre-built based on past data. Follow [this blog post](https://aws.amazon.com/blogs/machine-learning/detect-online-transaction-fraud-with-new-amazon-fraud-detector-features/) for more detailed instructions.
2. Clone this repo, navigate to the directory streaming-serverless-fraud-detection
3. Run the following commands:
```bash
cd kinesis-firehose-inline-enrichment
sam build
sam deploy --guided --stack-name kinesis-firehose-data-enrichment
```

### Try it out
To try this solution, we need to send data to the Kinesis Data Firehose. You can use [Kinesis Data Generator](https://github.com/awslabs/amazon-kinesis-data-generator) for that. Once you deployed the Data Generator and logged in, select Kinesis Data Stream that matches the one in the Outputs section of your deployed data enrichment sample stack. You can use the following command to get stack details (check Outputs for the stream name):

```bash
aws cloudformation describe-stacks --stack-name kinesis-firehose-data-enrichment
```

You can use the following template for transaction record generation:

```code=json
    {
        "transaction_id":"{{random.number({"min":10000, "max":100000})}}",
        "transaction_timestamp":"{{date.now("YYYY-MM-DDTHH:mm:ss")}}Z",
        "customer_email": "{{random.arrayElement(["admin@example.com","user@example.com","employee@example.com","customer@example.com"])}}",
        "order_price": "{{random.number({"min":10, "max":1000})}}",
        "product_category": "{{random.arrayElement(["kitchen","garden","groceries","leisure"])}}",
        "ip_address": "{{internet.ip}}",
        "card_bin": "{{random.number(
            {
                "min":1,
                "max":99999
            }
        )}}"
    }
```
**Note:** 
*Keep in mind Amazon Fraud Detector quotas for your account and use appropriate batch sizes (for example, send 10 records at a time).* 

Stop record generation after you send a few batches to the Kinesis Data Firehose. Wait for a couple of minutes and check transactions destination bucket (see name of the bucket in the stack outputs). 


### Cleaning Up
To avoid incurring further charges when you do not need this process anymore, run the following command:
```bash
sam delete --stack-name kinesis-firehose-data-enrichment 
```


## Event data inspection and fraud detection/prevention

### Overview
This architecture uses Step Functions to enable real-time EventBridge event inspection and fraud detection/prevention using Amazon Fraud Detector. It does not stop
processing of the potentially fraudulent transaction, rather flagging it for an additional review. We publish enriched transactions to an event bus that differs from the one that raw event data is being published to. 
This way, consumers of the data can be sure that all events include fraud detection results as metadata. The consumers can then inspect the metadata and apply their own rules based on the metadata. For example, in an event driven e-commerce application, a consumer can choose to not process the order if this transaction is predicted to be fraudulent. 
This architecture pattern can also be useful for detecting and preventing fraud in new account creation or during account profile changes ( like changing you address or phone number or credit card on file in your account profile).

![Architecture](./assets/architecture_event_enrichment.png)

Note, that you could use [EventBridge Pipes](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html) with an [Enrichment step](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html#pipes-enrichment) that uses Lambda to implement approach similar to the streaming data enrichment scenario above.

The flow of the events is as follows. 

1. We publish the financial transactions to EventBridge event bus. The source of the data could be a system that generates these transactions - for example, e-commerce, banking, etc. 
2. EventBridge rule starts Step Functions workflow execution
3. Step Functions Workflow receives the transaction and processes it: 
    - Calls the Amazon Fraud Detector API using GetEventPrediction action
        * The API returns either of these 3 results - “approve”, “block” or “investigate” 
    - Updates transaction data by adding fraud detection results
4. If transaction fraud prediction result is “block” or “investigate” - send a notification using Amazon SNS for further investigation
5. Step Functions Workflow publishes the updated transaction to the EventBridge bus for enriched data

As in Kinesis Data Firehose data enrichment, this architecture does not prevent fraudulent data from reaching the next step. It adds fraud detection metadata to the original event and sends notifications about potentially fraudulent transaction. It may be that consumers of the enriched data do not include business logics that uses fraud detection metadata in their decisions. In such case, you can change the Step Functions workflow so it does not put such transactions to the destination bus and route them to a separate event bus to be consumed by a separate “suspicious transactions” processing application.

### Deployment
1. The Fraud Detector model and the detector should be pre-built based on past data. Follow [this blog post](https://aws.amazon.com/blogs/machine-learning/detect-online-transaction-fraud-with-new-amazon-fraud-detector-features/) for more detailed instructions.
2. Clone this repo, navigate to the directory streaming-serverless-fraud-detection
3. Run the following commands:
```bash
cd eventbridge-event-detection
sam build
sam deploy --guided --stack-name eventbridge-event-fraud-detection
```

### Try it out

To try this solution, we need to publish events to the EventBridge. You can use [AWS CLI](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/events/put-events.html) or AWS Management Console EventBridge section for that. 


Following AWS CLI command will publish the event to the EventBridge bus (change event bus name and details as needed):

```bash
aws events put-events --entries '[{"EventBusName": "<EventBridge bus name here>", "Source": "com.example.transactions", "DetailType": "Transaction", "Detail": "{\n \"transaction_id\" : \"132467890123\", \"transaction_timestamp\" : \"2022-01-01T12:00:00Z\", \"customer_email\": \"customer@example.com\", \"order_price\": \"199.99\", \"product_category\": \"leisure\", \"ip_address\": \"127.0.0.1\", \"card_bin\": \"999999\" \n}"}]'

```

You can check Step Functions execution logs following the link in the stack outputs. Note that only errors are logged and that execution data is not included. 


You will need to specify the bus where you will publish events. Use the one in the Outputs section of your deployed fraud detection sample stack. You can use the following command to get stack details (check Outputs for the bus name):

```bash
aws cloudformation describe-stacks --stack-name eventbridge-event-fraud-detection
```


### Cleaning Up
To avoid incurring further charges when you do not need this process anymore, run the following command:
```bash
sam delete --stack-name eventbridge-event-fraud-detection 
```
