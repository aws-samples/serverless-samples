// lib/cognito-stack.ts
import * as cdk from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

export interface CognitoStackProps extends cdk.NestedStackProps {
  stageName: string;
}

export class CognitoStack extends cdk.NestedStack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: CognitoStackProps) {
    super(scope, id, props);

    this.userPool = new cognito.UserPool(this, "UserPool", {
      featurePlan: cognito.FeaturePlan.PLUS,
      removalPolicy:
        props.stageName === "dev"
          ? cdk.RemovalPolicy.DESTROY
          : cdk.RemovalPolicy.RETAIN,
      passwordPolicy: {
        minLength: 8,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      standardThreatProtectionMode:
        cognito.StandardThreatProtectionMode.FULL_FUNCTION,
    });

    this.userPoolClient = new cognito.UserPoolClient(this, "UserPoolClient", {
      userPool: this.userPool,
      authFlows: {
        userPassword: true,
        adminUserPassword: true,
      },
    });

    NagSuppressions.addResourceSuppressions(this.userPool, [
      {
        id: "AwsSolutions-COG2",
        reason: "Sample does not need MFA, would overcomplicate demo flow",
      },
    ]);
  }
}
