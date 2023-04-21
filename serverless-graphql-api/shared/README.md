# Shared Resources
These resources are available to integrate and use as boilerplate infrastructure-as-a-code (IaaC) templates.

## Amazon Cognito
[This template](cognito.yaml) creates an Amazon Cognito user and identity pools. Both authorized and unauthorized roles are created for the identity pool and an empty administrative user group is created in the User Pool. You will need to create appropriate policies and associate them with the roles created. Please note that this stack does not create an user interface that could be used for an interactive login and the User Pool callback URL points to the localhost.

To deploy this stack use the following command:

```bash
aws cloudformation create-stack --stack-name serverless-api-cognito --template-body file://cognito.yaml --capabilities CAPABILITY_IAM
```

After the stack is created you may need to create user account for authentication/authorization. 
_Note the Cognito user pool and application client ID in the stack outputs, you will use it in the commands below._

Use AWS CLI to create and confirm a user:

```bash
aws cognito-idp sign-up --client-id <cognito user pool application client id> --username <username> --password <password> --user-attributes Name="name",Value="<username>"
aws cognito-idp admin-confirm-sign-up --user-pool-id <cognito user pool id> --username <username> 
```

After this first step step your new user account will be able to access public data and create new bookings in your application. To perform administrative functions like adding locations and resources, you will need to navigate to AWS Console, select the Amazon Cognito service, select the User Pool instance that was created during this deployment, navigate to "Users and Groups", and add your user to the administrative users group. 

If you use the command line or third party tools such as Postman to test the APIs, you will need to provide an Identity Token in the request "Authorization" header. To obtain this token, authenticate with the Amazon Cognito User Pool using the AWS CLI command below (this command is also available in the SAM template outputs). The IdToken value will be present in the JSON output of the command. It is available in the stack outputs as well.

```bash
aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id <cognito user pool application client id> --auth-parameters USERNAME=<username>,PASSWORD=<password>
```

## Cleanup

To delete this stack use the following command ():

```bash
aws cloudformation delete-stack --stack-name serverless-api-cognito
```



 
