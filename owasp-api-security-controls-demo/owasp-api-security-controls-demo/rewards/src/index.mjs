import {
  CognitoIdentityProviderClient, AdminGetUserCommand
} from "@aws-sdk/client-cognito-identity-provider";

const client = new CognitoIdentityProviderClient({});
const USER_POOL= process.env.USER_POOL_ID

export async function handler(event) {
  console.log("Received event", JSON.stringify(event, 3));
  var userName = "NOT FOUND";
  var userEmail = "NOT FOUND"

  // Fetch user details from Cognito
  const command = new AdminGetUserCommand({
    UserPoolId: USER_POOL,
    Username: event.source.username,
  });

  const response = await client.send(command);
  console.log(response);

  response.UserAttributes.forEach(function(d){
    if (d.Name == "name") {
      userName = d.Value;
    }
    if (d.Name == "email") {
      userEmail = d.Value;
    }
  });

  // Build user object
  const user = {
    id: event.source.user_id,
    name: userName,
    email: userEmail
  }
  console.log(user);
  return user;
};

