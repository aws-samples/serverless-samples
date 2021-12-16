# Terraform / AWS SAM integration example project

[Terraform](https://www.terraform.io/) is an open-source infrastructure as code software tool that provides a consistent CLI workflow to manage cloud services. [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) (SAM) is an open-source framework for building serverless applications. Teams that choose to use both Terraform and SAM need a simple way to share resource configurations between tools. [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html) (SSM) can bridge this gap by providing secure, hierarchical storage for configuration data management and secrets management. This project demonstrates how to create a simple app using Terraform, SAM and SSM Parameter Store.

## Setup the project

1. Clone this repository. 

2. Follow the directions in this [README](./terraform/README.md) to create resources with Terraform. The Terraform file in this folder will create an [Amazon SQS](https://aws.amazon.com/sqs/) queue and store its arn in the [SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html).

3. Follow the directions in this [README](./sam/README.md) to create resources with [SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html). This SAM application will create an [AWS Lambda](https://aws.amazon.com/lambda/) function that uses the SQS queue as its event source. Notice in particular the [AWS CloudFormation dynamic reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html) contained in the `template.yaml` file that retrieves the SQS queue arn stored in SSM Parameter Store. 

4. Clean up. Both README files contain instructions for destroying the resources created in this project.

## Costs

### Systems Manager Parameter Store
The standard-parameter tier is the default tier when you begin to use Parameter Store. Using the standard-parameter tier, you can create 10,000 parameters for each AWS Region in an AWS account. The content size of each parameter can equal a maximum of 4 KB. There is no additional charge to use the standard-parameter tier.

Use the advanced-parameter tier to create a maximum of 100,000 parameters for each AWS Region in an AWS account. The content size of each parameter can equal a maximum of 8 KB. There is a charge to use the advanced-parameter tier. 
- [Systems Manager Parameter Store pricing](https://aws.amazon.com/systems-manager/pricing/)

### Terraform and SAM
There is no additional charge to use Terraform and SAM. With Terraform and SAM you are charged for the resources created by these tools.
- [Amazon SQS pricing](https://aws.amazon.com/sqs/pricing/)
- [AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/)

