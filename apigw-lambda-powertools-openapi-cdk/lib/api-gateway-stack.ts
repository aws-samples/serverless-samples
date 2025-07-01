// lib/api-gateway-stack.ts
import * as cdk from "aws-cdk-lib";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import * as path from "path";
import * as fs from "fs";
import { NagSuppressions } from "cdk-nag";

interface ApiGatewayStackProps extends cdk.NestedStackProps {
  handleLambda: lambda.Function;
  searchLambda: lambda.Function;
  stageName: string;
  userPool: cognito.UserPool;
}

export class ApiGatewayStack extends cdk.NestedStack {
  public readonly api: apigateway.SpecRestApi;

  constructor(scope: Construct, id: string, props: ApiGatewayStackProps) {
    super(scope, id, props);

    const openApiSpecContent = fs.readFileSync(
      path.join(__dirname, "openapi/openapi.json"),
      "utf8"
    );

    const openApiSpec = JSON.parse(
      openApiSpecContent
        .replaceAll("${lambdaArn}", props.handleLambda.functionArn)
        .replaceAll("${region}", cdk.Stack.of(this).region)
        .replaceAll("${searchLambdaArn}", props.searchLambda.functionArn)
        .replaceAll("${accountId}", cdk.Stack.of(this).account)
        .replaceAll("${userPoolId}", props.userPool.userPoolId)
    );

    const accessLogGroup = new logs.LogGroup(this, "ApiAccessLogs");

    this.api = new apigateway.SpecRestApi(this, "SampleApiGatewayLambda2Api", {
      restApiName: "OrdersAPI",
      description: "API Gateway with Lambda integration",
      apiDefinition: apigateway.ApiDefinition.fromInline(openApiSpec),
      deployOptions: {
        accessLogDestination: new apigateway.LogGroupLogDestination(
          accessLogGroup
        ),
        accessLogFormat: apigateway.AccessLogFormat.jsonWithStandardFields(),
        dataTraceEnabled: true,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        stageName: props.stageName,
        tracingEnabled: true,
      },
      cloudWatchRole: false,
    });

    new lambda.CfnPermission(this, "LambdaHandlerPermission", {
      action: "lambda:InvokeFunction",
      functionName: props.handleLambda.functionName,
      principal: "apigateway.amazonaws.com",
      sourceArn: `arn:aws:execute-api:${this.region}:${this.account}:${this.api.restApiId}/*/*/order*`,
    });

    new lambda.CfnPermission(this, "LambdaSearchPermission", {
      action: "lambda:InvokeFunction",
      functionName: props.searchLambda.functionName,
      principal: "apigateway.amazonaws.com",
      sourceArn: `arn:aws:execute-api:${this.region}:${this.account}:${this.api.restApiId}/*/*/orders/search*`,
    });

    NagSuppressions.addResourceSuppressions(this.api, [
      {
        id: "AwsSolutions-APIG2",
        reason: "for SpecRestApi defined in the OpenAPI spec",
      },
    ]);
    NagSuppressions.addResourceSuppressions(this.api.deploymentStage, [
      {
        id: "AwsSolutions-APIG3",
        reason: "demo does not need WAF, unreasonable cost increase",
      },
    ]);
  }
}
