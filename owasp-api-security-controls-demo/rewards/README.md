# Rewards service
The rewards service is an internal service accessed by marketing team to run campaigns and data science team to train predictive models to personalise customer experience. It is exposed using [AWS AppSync](https://aws.amazon.com/appsync/), a managed [GraphQL](https://graphql.org/) API. [Amazon Cognito](https://aws.amazon.com/pm/cognito) is used to authenticate users. The API allows listing order and associated user details. For this demo, we have created this as a public facing API to simplify testing. AppSync supports [private APIs](https://aws.amazon.com/blogs/mobile/introducing-private-apis-on-aws-appsync/).

![Rewards service architecture](../assets/RewardsService.png)

This scenario demonstrates mitigation for the following OWASP risks.

|Risk|Description|Control|
| -- | --------- | ----- |
|API2:2023|Broken Authentication|Cognito authorizer|
|API3:2023|Broken Object Property Level Authorization|Role based access control based on custom claim for GraphQL Type field|
|API5:2023|Broken Function Level Authorization|Role based access control based on custom claim for GraphQL Query|

## How it works

### Retrieving order and user details

The AppSync API allows listing orders with a Query as shown in the top left of the diagram above. API is locked with the Cognito user pool created for the [Order service](../order/README.md). The query combines data from two sources. It gets order details from the Orders DynamoDB table using native DynamoDB resolver (top right of diagram above). It gets user details from Cognito using a Lambda function as resolver (bottom right of diagram above). The Lambda function receives the username from the Orders data and invokes the [`AdminGetUser`](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_AdminGetUser.html) API to get user full name and email attributes.

## Testing controls

### Prerequisites

1. You must deploy the stack and configure Cognito users as explained in the [README](../README.md) file in the root of this project
2. [Optional] Install [`jq`](https://jqlang.github.io/jq/download/) to make it easy to review query output.

### Mitigation for broken authentication
1. You need the Reward API endpoint, Cognito user pool name, and Cognito client id. You can get both from the terminal where you ran the deploy command. Alternately, run `sam list stack-outputs --stack-name <stack name>` to retrieve this. We will use the sample GraphQL query [sample_query.gql](./graphql/sample_query.gql). Run the curl command below. It has no authorization header.

```bash
curl -H "Content-Type: application/json" -XPOST https://<api id>.appsync-api.<region>.amazonaws.com/graphql -d @rewards/graphql/sample_query.gql
```

The request above will fail.

```bash
{
  "errors" : [ {
    "errorType" : "UnauthorizedException",
    "message" : "You are not authorized to make this call."
  } ]
}
```

### Mitigation for broken object property level authorization
2. Marketing user needs access to PII data such as email for running marketing campaign. In a real world scenario, you will have a custom attribute to indicate if user has opted out of campaigns to further filter the data retrieved. The data science team is also interested in this data to build personalisation model. While they need access to user attributes such as geographic location or tenure on the platform but must not have access to PII data. GraphQL allows you to set fine-grained permissions against fields. Review the [graphql schema](./graphql/schema.graphql). The `user` field on type `Order` has authentication set to `@aws_auth(cognito_groups: ["Marketing"])`. Also note that the permisison on the Query itself allows both Marketing and Datascience Cognito groups access.

To test this, try invoking the AppSync endpoint as marketing user. First authenticate as `marketing` to retrieve JWT tokens.

```bash
aws cognito-idp admin-initiate-auth --user-pool-id <cognito user pool> --client-id <client if> --auth-flow ADMIN_NO_SRP_AUTH --auth-parameters 'USERNAME=marketing,PASSWORD="<marketing password>"'
```

Invoke the AppSync endpoint using the Id token from command above as `Authorization` header.

```bash
curl -H "Content-Type: application/json" -H "Authorization: <id token>” -XPOST https://<api id>.appsync-api.<region>.amazonaws.com/graphql -d @rewards/graphql/sample_query.gql | jq '.'
```

You should see an output like this. It has been truncated for brevity. 

```json
{
  "data": {
    "listOrders": {
      "items": [
        {
          "item": "Oatmilk Latte",
          "order_date": "2024-06-01T07:08:42.416249+00:00",
          "amount": 7.0,
          "user": {
            "email": "mary@example.com",
            "name": "MaryMajor"
          },
          "user_id": "299a05cc-4091-7076-4751-9a34d1c732ec"
        },
        ...
      ]
    }
  }
}
```

3. Now rerun the same commands as datascience user. First, authenticate with Cognito as `datascientist` and use the id token to invoke AppSync. You will see `null` for user data. The response will also include an error field that explains why this is null. The frontend application will handle this is a real world scenario.

```json
{
  "data": {
    "listOrders": {
      "items": [
        {
          "item": "Oatmilk Latte",
          "order_date": "2024-06-01T07:08:42.416249+00:00",
          "amount": 7.0,
          "user": null,
          "user_id": "299a05cc-4091-7076-4751-9a34d1c732ec"
        },
        ...
      ]
    }
  },
  "errors": [
    {
      "path": [
        "listOrders",
        "items",
        0,
        "user"
      ],
      "data": null,
      "errorType": "Unauthorized",
      "errorInfo": null,
      "locations": [
        {
          "line": 1,
          "column": 151,
          "sourceName": null
        }
      ],
      "message": "Not Authorized to access user on type Order"
    },
    ...
  ]
}
```

### Mitigation for broken function level authorization
1. Cognito is the default authentication but not all Cognito users can access the data. Try authenticating as `mary` and use the Id token for the curl command. This will return message below.

```json
{
  "data": {
    "listOrders": null
  },
  "errors": [
    {
      "path": [
        "listOrders"
      ],
      "data": null,
      "errorType": "Unauthorized",
      "errorInfo": null,
      "locations": [
        {
          "line": 1,
          "column": 22,
          "sourceName": null
        }
      ],
      "message": "Not Authorized to access listOrders on type Query"
    }
  ]
}
```

