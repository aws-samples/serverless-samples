# OWASP API security controls demo

This example demonstrates how you can mitigate for application focused [OWASP API security risks](https://owasp.org/API-Security/) when using [Amazon API Gateway](https://aws.amazon.com/api-gateway/) and [AWS AppSync](https://aws.amazon.com/pm/appsync) to build APIs. The sample code focuses on the following risks.

| Risk | Description |
| ---- | ----------- |
|API1:2023|Broken Object Level Authorization|
|API2:2023|Broken authentication|
|API3:2023|Broken Object Property Level Authorization|
|API5:2023|Broken Function Level Authorization|

The controls demonstrated in this example must be used in conjunction with perimeter security controls. We will use the example of a microservice based coffee shop application below to demonstrate the controls.

> Note: Controls here rely on native AWS services. But there are multiple ways to implement them. You can also use open source or third party tools. The exact solution and choice of tools will depend on your use case. We encourage you to have a discussion with your AWS account team to dive deeper to identify the best solution for you.

![Coffee Shop Microservices Architecture](./assets/OverallArchitecture.png)

## How it works

Brief summary of the components below. Refer to the respective service folder to understand the security controls in place and how to test them.

* **[Order service](./order/README.md)**: End users use their mobile app to order coffee. This service is also used by internal admin employees to track all orders.
* **[Payment service](./payment/README.md)**: The order service relies on this to fulfil payments. In a real-world scenario, this will communicate with external payment gateways.
* **[Fulfillment service](./fulfillment/README.md)**: Baristas access this internal service to view and process outstanding coffee orders.
* **[Rewards service](./rewards/README.md)**: Marketing team accesses this internal service to understand user behaviour to run targeted marketing campaigns. Data science team also uses this data to train personalization models.

## Deployment instructions

### Prerequisites
1. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
2. [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
3. [Docker](https://docs.docker.com/engine/install/) or alternatives
4. Access to AWS account with permissions to deploy services used in this demo

### Steps

1. **Configure variables for deployment**
   
   Clone the git repository and navigate to this folder. This code relies on existing VPC and  subnets to deploy the services. You also need valid email addresses to configure users for the application. 
   
   Copy the file `samconfig.toml.example` at the root of this folder to `samconfig.toml`. Replace values in angular brackets `<>` in `samconfig.toml` with ones specific for your deployment. 
   
   Note:
   1. Please specify valid email address as you will receive temporary password on this email. You need this for subsequent steps. If you get the email address wrong, you will have to delete and redeply the stack as Amazon Cognito will not allow updating emails.
   2. Specify existing VPC and subnet ids in the region you are deploying to.

   ```bash
   cp samconfig.toml.example samconfig.toml
   ```

   > Tip: Use sub-addressing or `+` sign to distinguish the email addresses for the 5 users.

2. **Build and deploy the stack**
   
   Build and deploy the SAM template. We recommend using container for build. AWS Lambda functions used in this example are `arm64` based. Make sure you have Docker running before you run these commands.

   ```bash
   sam build --use-container
   sam deploy
   ```

3. **Configure Cognito users**

   The SAM template sets up 5 users to test our application. You must first set the password for these users in order to test the application. You will receive an email with temporary password from `no-reply@verificationemail.com <no-reply@verificationemail.com>` to the email addresses you configured in `samconfig.toml`.
   
   |Username|Purpose|samconfig field|
   | ------ | ----- | ------------- |
   |mary|End user accessing the order service|Customer1Email|
   |paulo|End user accessing the order service|Customer2Email
   |admin|Admin user accessing the order service|AdminEmail|
   |marketing|Marketing user accessing the rewards service|MktgEmail|
   |datascientist|Datascientist accessing the rewards service|DatascientistEmail|

   We will use the AWS CLI to set a new password for each user. You need the Cognito user pool id and user pool client in order to do this. You can get this on the terminal where you ran the deploy command in step 2. Alternately you can run `sam list stack-outputs --stack-name <stack name>`.

   **3.1.** Authenticate with Cognito using the temporary password. As an example, for Mary, this command is as follows. Replace `<temp password in email>` with the one you received in the email address you specified for Mary.

   ```bash
   aws cognito-idp admin-initiate-auth \
     --user-pool-id <user pool id> \
     --client-id <client id> \
     --auth-flow ADMIN_NO_SRP_AUTH \
     --auth-parameters 'USERNAME=mary,PASSWORD="<temp password in email>"'
   ```

   This command will return a session token. Sample output below.

   ```json
   {
        "ChallengeName": "NEW_PASSWORD_REQUIRED",
        "Session": "<redacted>",
        "ChallengeParameters": {
            "USER_ID_FOR_SRP": "mary",
            "requiredAttributes": "[\"userAttributes.name\"]",
            "userAttributes": "{\"name\":\"MaryMajor\",\"email\":\"mary@example.com\"}"
        }
    }
   ```

    **3.2.** Use the session token and respond to the challenge to set a new password. Command below for Mary.

    ```bash
    aws cognito-idp admin-respond-to-auth-challenge \
      --user-pool-id <user pool id> \
      --client-id <client id> \
      --challenge-name NEW_PASSWORD_REQUIRED \
      --challenge-response 'USERNAME=mary,NEW_PASSWORD="<new password>"' \
      --session '<Session token from above command>'
    ```

    This command will return id token, access token, and refresh token. We will use the id token later on to test our controls.

    ```json
    {
        "ChallengeParameters": {},
        "AuthenticationResult": {
            "AccessToken": "<redacted>",
            "ExpiresIn": 3600,
            "TokenType": "Bearer",
            "RefreshToken": "<redacted>",
            "IdToken": "<redacted>"
        }
    }
    ```

    Repeat these commands for the remaining 4 users. 

## Testing instructions

Please refer to the Readme in service sub-folders for test instructions.

## Cleanup instructions

1. Terminate the EC2 instance you created to test [payment service](./payment/README.md). If you wish to retain instance, make sure you detach the security group created by this stack. Else you won't be able to delete the stack.
2. Delete the rest of the components by running the command below from root of this folder.

```bash
sam delete
```
