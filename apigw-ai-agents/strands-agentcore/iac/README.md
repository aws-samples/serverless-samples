# Bedrock Knowledge Base CloudFormation Stack

## Deployment

Before deploying Amazon Bedrock Knowledge Base, you will need content in an Amazon S3 bucket that will be indexed during the deployment process. Create S3 bucket in the same AWS region you are deploying rest of your resources, upload data in the [formats supported](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ds.html), you will need it during the deployment.

To deploy Knowledge Base for the API Expert agent use following command:
```bash
aws cloudformation deploy --template-file ./bedrock-kb-s3.yaml --stack-name api-expert-kb --capabilities CAPABILITY_IAM --parameter-overrides ExistingS3BucketName=<your-expert-s3-bucket-name-here> IncludePublicDocs=false
```

By default, the Knowledge Base does not include publicly available AWS documentation (API Gateway documentation, white papers, etc.). You can control whether to include the public documentation by using the `IncludePublicDocs` parameter:

```bash
aws cloudformation deploy --template-file ./bedrock-kb-s3.yaml --stack-name api-expert-kb --capabilities CAPABILITY_IAM --parameter-overrides ExistingS3BucketName=<your-expert-s3-bucket-name-here> IncludePublicDocs=true
```

**NOTE**: *WEB data source is currently (end of 2025) only supported for knowledge bases created with an Amazon OpenSearch Serverless vector database. Stack deployment will faiul if you including public documents. We will keep this feature available so you can use it once web datra source becomes available for the knowledge vases created with S3 Vectors. Meanwhile you can add copies of the public documents to the S3 bucket.*

The template uses a conditional resource creation pattern:
1. When `IncludePublicDocs` is set to "true" (default), both S3 and public documentation data sources are created
2. When `IncludePublicDocs` is set to "false", only the S3 data source is created
3. The ingestion job automatically adapts to include only the data sources that were created

*Note: You may implement a scheduled task to re-synchronize data sources on a regular basis to keep those public documents in the knowledge base up to date.*

