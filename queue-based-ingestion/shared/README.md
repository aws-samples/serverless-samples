# Shared Resources

These resources are available to integrate and use as a boilerplate infrastructure-as-a-code (IaaC) templates.

## Amazon Cognito

[This template](cognito.yaml) creates Amazon Cognito user and identity pools and roles. Please note that this stack does not create UI that could be used for interactive login and User Pool callback URL points to the localhost.

To deploy this stack use the following command:

```bash
cd shared
aws cloudformation create-stack --stack-name queue-based-ingestion-cognito --template-body file://cognito.yaml --capabilities CAPABILITY_IAM
```

After stack is created you may need to create user account for authentication/authorization.

Use AWS CLI to create and confirm a user:

```bash
aws cognito-idp sign-up --client-id <cognito user pool application client id> --username <username> --password <password> --user-attributes Name="name",Value="<username>"

```

While using command line or third party tools such as Postman to test APIs, you will need to provide Identity Token in the request "Authorization" header. You can authenticate with Amazon Cognito User Pool using AWS CLI (this command is also available in SAM template outputs) and use IdToken value present in the output of the command (it is available in the stack outputs as well):

```bash
aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id <cognito user pool application client id> --auth-parameters USERNAME=<username>,PASSWORD=<password>
```

To delete this stack use the following command ():

```bash
aws cloudformation delete-stack --stack-name queue-based-ingestion-cognito
```

**Customizations necessary before using**
Edit policy to tighten permissions as needed.

**Outputs**

- UserPool - Cognito User Pool ID
- UserPoolClient - Cognito User Pool Application Client ID
- IdentityPool - Cognito Identity Pool ID
- CognitoIdentityPoolAuthorizedUserRole - IAM role for Cognito Identity Pool authorized users
- CognitoLoginURL - Cognito User Pool Application Client Hosted Login UI URL
- CognitoAuthCommand - AWS CLI command for Amazon Cognito User Pool authentication
