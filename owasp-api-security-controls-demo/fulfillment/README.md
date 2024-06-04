# Fulfillment service

The fulfillment service is used by baristas to close coffee orders. The baristas will access the orders over a private REST API Gateway. [AWS IAM](https://aws.amazon.com/iam) is used for authentication.

Users of this application are internal. The easiest way to vend AWS credentials is to federate the corporate identity provider to AWS. The AIM roles on AWS will provide access to the API. This in a real world will be managed by the application the users access.

![Payment service architecture](../assets/FulfillmentService.png)

This scenario demonstrates mitigation for the following OWASP risks.

|Risk|Description|Control|
| -- | --------- | ----- |
|API1:2023|Broken Object Level Authorization|Role based access control based on IAM permissions|
|API2:2023|Broken Authentication|IAM|
|API3:2023|Broken API Object Property Level Authorization|API Gateway Input validation|

## How it works

This service has 2 interfaces. The first is a queue based interface that accepts orders from the order service. A lambda function persists orders in a DynamoDB table with status as "PENDING". The API gateway integrates with another Lambda function to retrieve outstanding orders and update order status.

### Listing outstanding orders

The `listPendingOrders` resource uses a global index to query orders at status "PENDING".

### Updating order

As baristas pick up orders for processing, they can move the order to IN_PROGRESS and finally "CLOSE" them. The `updateOrderStatus` resource accepts a POST request to update order status.

## Testing controls

The steps are similar to testing the Payment service. Please refer to [Payment service instructions](../payment/README.md#testing-controls).