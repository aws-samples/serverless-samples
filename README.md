# Serverless Samples

This repository contains samples of Serverless application code.

- ## lambda-ecs-dual-deploy 

  This AWS Lambda / ECS Dual Deploy Sample Application demonstrates the steps necessary to build a container image that runs on both AWS Lambda and on another container service like AWS Elastic Container Service (ECS).

  [[README]](./lambda-ecs-dual-deploy)

- ## serverless-rest-api

    These REST API examples demonstrate end-to-end implementations of a simple application using a serverless approach that includes CI/CD pipelines, automated unit and integration testing, and workload observability. The examples include multiple implementations of the same application using a variety of development platform and infrastructure as a code approaches. The patterns here will benefit beginners as well as seasoned developers looking to improve their applications by automating routine tasks. [[README]](./serverless-rest-api)

- ## terraform-sam-integration 

  [Terraform](https://www.terraform.io/) is an open-source infrastructure as code software tool that provides a consistent CLI workflow to manage cloud services. [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) (SAM) is an open-source framework for building serverless applications. Teams that choose to use both Terraform and SAM need a simple way to share resource configurations between tools. [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html) (SSM) can bridge this gap by providing secure, hierarchical storage for configuration data management and secrets management. This project demonstrates how to create a simple app using Terraform, SAM and SSM Parameter Store. [[README]](./terraform-sam-integration) 

- ## apigw-private-custom-domain-name

  Implements a workaround solution for custom domain names for Amazon API Gateway private endpoints as described in the [blog post](https://georgemao.medium.com/enabling-private-apis-with-custom-domain-names-aws-api-gateway-df1b62b0ba7c). [[README]](./apigw-private-custom-domain-name)

- ## fargate-rest-api

  These examples focus on creating REST APIs with Amazon API Gateway, Amazon ECS, and AWS Fargate. The examples include CI/CD pipelines, automated unit and integration tests, as well as workload observability. The examples include multiple implementations of the same application using a variety of development platform and infrastructure as a code approaches. The patterns here will benefit beginners as well as seasoned developers looking to improve their applications by automating routine tasks. [[README]](./fargate-rest-api)

- ## fargate-private-api

  These private API examples, using Amazon API Gateway REST APIs, utilizes private API, and private integration, along with Amazon Cognito as the identity provider. The patterns here will benefit high security compliance organizations, such as Public Sector customers, to implement end to end private serverless APIs. The examples include CI/CD pipelines, automated unit and integration tests, as well as workload observability. [[README]](./fargate-private-api)

- ## multiregional-private-api

  The AWS global footprint enables customers to support applications with near zero Recovery Time Objective (RTO) requirements. Customers can run workloads in multiple regions, in a multi-site active/active manner, and serve traffic from all regions. To do so, developers often need to implement private multi-regional APIs that are used by the applications.  This example shows how to implement such a solution using Amazon API Gateway and Amazon Route 53. [[README]](./multiregional-private-api)

- ## apigw-ws-integrations

  Developers use the WebSocket protocol for bidirectional communications in their applications. With Amazon API Gateway [WebSocket APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html) you can build bidirectional communication applications without having to provision and manage servers. Many WebSocket samples use AWS Lambda or HTTP(s) as the integration targets and for connect/disconnect routes. This example uses the AWS service integration pattern to show how to simplify serverless architectures. It also shows you how to implement URL path support for WebSocket APIs in Amazon API Gateway using Amazon CloudFront and CloudFront Functions. [README](./apigw-ws-integrations)

- ## apigw-readme-integration
  Amazon API Gateway publishes a regularly updated [Serverless Developer Portal application](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-developer-portal.html) in the [AWS Serverless Application Repository](https://aws.amazon.com/serverless/serverlessrepo/) and on [GitHub](https://github.com/awslabs/aws-api-gateway-developer-portal). However, there may be cases when this application is not enough. In such cases, we recommend looking at our partner solutions that may fit your needs. This example shows how to integrate one of the partner solutions, [ReadMe.com](https://readme.com/), with Amazon API Gateway to make sure that your documentation is up to date and gets changed every time you change the API. [README](./apigw-readme-integration)

 - ## streaming-serverless-fraud-detection 
   Online fraud has a widespread impact on businesses and requires an effective end-end strategy to detect and prevent new account fraud, account takeover and stop suspicious payment transactions. Detecting fraud closer to the time of fraud occurrence is key to the success of a fraud detection and prevention system. This example demonstrates a serverless approach to detect online transaction fraud in near real-time. It shows how detection can be plugged into various data streaming and event- driven architectures, depending on the outcome to be achieved and actions to be taken to prevent fraud - alert the customer/user about the fraud, flag the transaction for additional review, etc. [README](./streaming-serverless-fraud-detection)

- ## serverless-graphql-api
   These GraphQL API examples show end-to-end implementations of a simple application using a serverless approach that includes CI/CD pipelines, automated testing, and workload observability. [README](https://github.com/aws-samples/serverless-samples/tree/main/serverless-graphql-api) 

- ## queue-based-ingestion
  This example demonstrates Amazon API Gateway and Amazon Simple Queue Service (Amazon SQS) integration capabilities. However rather than just focusing on technical aspects, we have used a common use case of triggering long-running batch processes with very minimal input. A reference application is created to showcase the implementation of this use case using a serverless approach that includes CI/CD pipelines, automated unit and integration testing, and workload observability. [README](./queue-based-ingestion)

- ## owasp-api-security-controls-demo
  This example demonstrates controls to mitigate application centric [OWASP API security risks](https://owasp.org/API-Security/editions/2023/en/0x11-t10/) for a sample microservice application using Amazon API Gateway and AWS AppSync. Refer to [README](./owasp-api-security-controls-demo) for details.

- ## apigw-log-analytic
  This solution provides analytics for Amazon API Gateway (REST endpoints). It visualizes and analyzes API Gateway access logs using an Amazon QuickSight dashboard. This pre-built dashboard enables you to analyze API usage by visualizing various components. These visuals include customer identifiers with usage plans, helping developers identify popular routes, errors, authentication methods, and users reaching quota limits. [README](./apigw-log-analytic)

## Security

See [CONTRIBUTING](./CONTRIBUTING.md#security-issue-notifications) for more information.

## Code of Conduct

See [CODE OF CONDUCT](./CODE_OF_CONDUCT.md) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file.
