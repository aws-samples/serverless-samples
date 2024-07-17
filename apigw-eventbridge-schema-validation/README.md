# Automating event validation with EventBridge and API Gateway

Validation of events is a simple concept, but putting it into practice in an enterprise environment can be challenging. Generating, managing and applying schemas across multiple environments and teams requires coordination and automation.  Finding the right balance of speed and governance can be tricky.  By incrementally increasing governance at the right stages of the event lifecycle and using AWS services to automate schema generation and validation, you can enable developers to move quickly while applying the right level of governance.  This solution will focus on automating schema creation, modification, promotion and enforcement.

[Amazon Eventbridge](https://aws.amazon.com/eventbridge/) is a serverless event bus that can perform discovery and versioning of event schemas.  Event consumers can download schemas and code bindings to validate events and speed up development.  This provides the freedom for developers to create events without having to worry about managing schemas. Discovered schemas serve their purpose for consumer validation of events, but what about validating events before they are routed downstream to consumers?  Schema validation is not currently a native feature of Eventbridge; however, API Gateway models can be used to validate requests.  By placing API Gateway in front of the event bus, you can validate requests as well as implement caching, authorization, rate limiting and other features of the service.  In this solution you'll learn through examples how to automate schema notification, modification, promotion and enforcement.  

![Architecture flow of producer and consumer](./assets/Producer_Consumer.png)
<p style="text-align:center; font-style: italic"> Figure 1: Producers and consumers with schema discovery </p>

Before we dive into the solution, let's discuss three stages of event evolution.  You can find a reference to these stages in a [talk by Sam Dengler](https://youtu.be/-Pv_kYflEEg?si=a7CDRdnGPtSH1agk&t=808).  As events evolve from inception to production, its important consumers can discover and understand event structure and how it changes over time.  Events go through multiple iterations of testing and refinement, similar to how an application evolves toward production.  

Events start as raw information, a skeleton of what the event will eventually look like.  This allows developers to rapidly build, test and refine event structures without any dependence on the event.  The second stage is where events are exposed to consumers within the bounded context.  This enables consumers to test events within a limited scope, ensuring they meet requirements within their context.  The third stage is where events are expanded to include other business and technical related metadata.  This may involve adding required fields and any additional refinement required by consumers to effectively process the event across many bounded contexts or business domains.


Let's use a fictitious example of a Healthcare scheduling system.  In this example, the producer's job is to create a surgical scheduled event.  In the first phase, we put together the skeleton of the event.  This might include the date, time, location, type of surgery and surgeon.  

**Stage 1**
```json
{
   ...
   "detail": {
         "schedule": {
            "date": "5/15/2024",
            "time": "10:00 AM",
            "location": "Building 6"
         },
         "surgery": {
            "surgeon": "John Thomas",
            "type": "Orthopedic"
         }
   }
}

```

In the next stage, the event is refined within the surgery team's bounded context.  At this stage, you may get feedback to include requirements for the type of anesthesia and further details about the type of surgery (ACL), medication and other related data. 

**Stage 2**

```json
{
   ...
   "detail": {
         "surgery": {
            "schedule": {
               "date": "5/15/2024",
               "time": "10:00 AM",
               "location": "Building 6",
               "duration": "120 mins"
            },
            "medication": "Oxycodone 5 mg every 4 hours.",
            "team": {
               "surgeon": "Jane Someone", 
               "assistant": "John Person"
            },
            "procedure": {
               "type": "Anterior Cruciate Ligament",
               "location": "left knee"
               ...
            }
         }
   }
}

```

In the last stage, you bring in other bounded contexts and consumers.  Here you might need to know if and what types of therapy are required and where those will occur.  We may have follow-up appointments and reminder details.  

**Stage 3**
```json
{
   ...
   "detail": {
         "surgery": {
            "schedule": {
               "date": "5/15/2024",
               "time": "10:00 AM",
               "location": "Building 6",
               "duration": "120 mins"
            },
            "therapy": {
               "OT": "yes",
               "PT": "yes"
            },
            "medication": "Oxycodone 5 mg every 4 hours.",
            "team": {
               "surgeon": "Jane Someone", 
               "assistant": "John Person"
            },
            "follow-ups": [
               "5/25/2024", "6/10/2024", "9/10/2024"
            ],
            "procedure": {
               "type": "Anterior Cruciate Ligament",
               "location": "left knee"
               ...
            }
        }
   }
}

```
Next, you'll apply governance to events through each of these stages. The next section covers two solutions using schema discovery to provide automated validation to events.  

# Architecture and Implementation

## Direct Lambda Schema Updater
The following architecture uses Eventbridge schema discovery to generate new schema versions, download, process and post the schema to an API Gateway model for request validation.  The Lambda schema updater function will trigger on schema version changes.  
![Lambda based schema updater](./assets/Continuous_Lambda.png)

## CI CD Driven Schema Updater
Another option is to control these changes through your CI CD pipeline.  The schema updater can act as a means to download, process and upload new schema versions to a Git repository or S3 bucket.  This allows for additional testing and checks before schemas are promoted and enforced.
![CI CD driven schema updater](./assets/CI_CD_Updater.png)

## Implementation  Through Stages 
Let's review the implementation through each stage. 

### Stage 1
This is the stage where raw events are being produced and there are no consumers dependent on the events.  Here, the development team is producing events at will through Eventbridge with no model validation applied.  The schema updater is toggled off.  Schemas will be discovered and versioned, but not applied to requests. 

### Stage 2
In this stage, events are starting to build a solid domain structure and are tested within a bounded context.  Your team has the option of applying request validation when it's appropriate.  Since there are consumers within the same bounded context, you can start enforcing validation, balancing it with active development.  The decision to enforce request validation should be based on testing and feedback from the consumers in this stage.  This is where the CI CD approach can provide additional safeguards and oversight because you can base your schema updates on successful iterations of test runs in your pipeline.   

### Stage 3
This is the final stage where events grow into the full business context required to process them downstream.  You also have additional consumers that rely on our events providing the necessary structure and information.  Request validation is based on your unique business needs, but is highly encouraged at this stage to ensure valid events are produced and routed downstream.  Events that don't follow schema requirements will be rejected before any downstream routing or processing is applied.  This improves speed and reduces unnecessary downstream processing. 

## Deployment

_The following solution uses the Lambda based schema updater architecture referenced above.  You can modify the SAM template and Lambda function to also use this approach for CI CD driven updates._

### Pre-Requisites

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) (AWS SAM) installed
* [NPM](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) installed

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

### Deployment Steps

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/serverless-patterns
    ```
1. Change directory to the pattern directory:
    ```
    cd serverless-patterns/apigw-eventbridge-schema-validation
    ```
1. From the command line, use NPM to install dependencies and AWS SAM to deploy the AWS resources for the pattern as specified in the template.yml file:
    ```
    npm install --prefix lambda 
    sam build && sam deploy --guided
    ```
1. During the prompts:
    * Enter a stack name
    * Enter the desired AWS Region
    * For the parameters, you can accept the defaults. 
   *  Allow SAM CLI to create IAM roles with the required permissions.

Once you have run `sam deploy --guided` mode once and saved arguments to a configuration file (samconfig.toml), you can use `sam deploy` in future to use these defaults.  

Copy the API URL from the output for later use in the testing section.

## Testing

This first test will emulate the first stage of our event evolution.  A schema will be created in Eventbridge, but won't be enforced in API Gateway until you enable the rule to trigger the Lambda function.  This will be done in the second test.

Run this command multiple times to send events to the custom event bus. Replace API URL with your API endpoint. 

```
curl --location --request POST '<YOUR API URL>' \
--header 'Content-Type: application/json' \
--data-raw '{
  "detail-type": "surgical",
  "source": "scheduling.event",
  "detail": {
      "schedule": {
        "date": "5/15/2024",
        "time": "10:00 AM",
        "location": "Building 6"
      },
      "team": {
          "surgeon": "Jane Someone",
          "assistant": "John Person"
      }
  }
}'
```
You can validate this event was processed by the Event Bus by viewing the Cloudwatch scheduling-events-source-catch-all log group for events.  The SAM template contains a catch-all rule for any source match.

Schema generation can take up to 5 minutes.  You can view status of discovered schemas by running the following AWS CLI command.  If you receive an error stating it doesn't exist, wait and try again.
```
aws schemas list-schema-versions --schema-name scheduling.event@Surgical --registry-name discovered-schemas
```

Here's an example output, if successful:
```
{
    "SchemaVersions": [
        {
            "SchemaArn": "arn:aws:schemas:us-west-2:294626376751:schema/discovered-schemas/scheduling.event@Surgical",
            "SchemaName": "scheduling.event@Surgical",
            "SchemaVersion": "1",
            "Type": "OpenApi3"
        }
    ]
}
```

Once the first schema version is created, you can move on to the next step.  To test the second stage, first turn on the rule to trigger the Lambda function on schema creation by running this command to enable the Eventbridge rule and accept ('y') deployment of the changeset: 
```
sam deploy --parameter-overrides SchemaEnforcementEnabledOrDisabled=ENABLED
```
<p id="stage2-cmd"> </p> With the rule enabled, run the following command to send another event to the custom event bus. 

```
curl --location --request POST '<YOUR API URL>' \
--header 'Content-Type: application/json' \
--data-raw '{
  "detail-type": "surgical",
  "source": "scheduling.event",
  "detail": {
        "schedule": {
          "date": "5/15/2024",
          "time": "10:00 AM",
          "location": "Building 6",
          "duration": "120 mins"
        },
        "medication": "Oxycodone 5 mg every 4 hours.",
        "team": {
          "surgeon": "Jane Someone",
          "assistant": "John Person"
        },
        "procedure": {
          "type": "Anterior Cruciate Ligament",
          "location": "left knee"
        }
  }
}'
```
Eventbridge will generate a new schema version, which could take several minutes to complete.  Request validation will not be set until after the schema version is created.  You can run the same command from the first test to view schema versions.  You should see a new schema version created.  

Run the following command again and wait until a second schema version exists.
```
aws schemas list-schema-versions --schema-name scheduling.event@Surgical --registry-name discovered-schemas
```

Here's an example output with version 2 now available: 
```
{
    "SchemaVersions": [
        {
            "SchemaArn": "arn:aws:schemas:us-west-2:294626376751:schema/discovered-schemas/scheduling.event@Surgical",
            "SchemaName": "scheduling.event@Surgical",
            "SchemaVersion": "2",
            "Type": "OpenApi3"
        },
        {
            "SchemaArn": "arn:aws:schemas:us-west-2:294626376751:schema/discovered-schemas/scheduling.event@Surgical",
            "SchemaName": "scheduling.event@Surgical",
            "SchemaVersion": "1",
            "Type": "OpenApi3"
        }
    ]
}

```


With the Lambda trigger now enabled, the latest schema is downloaded, processed and uploaded to API Gateway replacing the current request validator.  You can view the output from the Lambda function by viewing its Cloudwatch logs.

Future requests will now use the latest schema generated from Eventbridge. You can test this by sending in an event that does not have all the required fields from the latest event. 

```
curl --location --request POST '<YOUR API URL>' \
--header 'Content-Type: application/json' \
--data-raw '{
  "detail-type": "surgical",
  "source": "scheduling.event",
  "detail": {
      "surgery": {
        "schedule": {
          "date": "5/15/2024",
          "time": "10:00 AM",
          "location": "Building 6",
          "duration": "120 mins"
        }
      }
  }
}'
```
Required objects and properties have been removed, which will be caught by the request validator and rejected.  Note: if your event is passed through successfully, you may need to wait for the new schema version to be created and processed.

```
{ "message": "[object has missing required properties ([\"medication\",\"procedure\",\"schedule\",\"team\"])]"}% 
```

Run the [first request from stage two](#stage2-cmd) again with all required fields and the validator will pass the event through to Eventbridge.  With the trigger enabled, any new schema versions created will trigger an update to the API Gateway model.  If you want to optionally disable schema updates at any point, run the command below.  This disables the rule in Eventbridge that triggers the Lambda function to update the API Gateway model with a new schema.  This is not required for the next step.  

```
sam deploy --parameter-overrides SchemaEnforcementEnabledOrDisabled=DISABLED
```

The schema update feature can be leveraged across environments and API deployments to quickly enable and disable schema validation at the request level.  No additional code is required to perform the schema validation.  To scale validators to additional resources and methods, add request validator definitions to the SAM template under the appropriate path(s).

To test the third stage, send an event with a broader business context, which will generate another schema version.  If the schema update rule and trigger are still enabled, the API Gateway model will be updated with the latest schema from this event.

```
curl --location --request POST '<YOUR API URL>' \
--header 'Content-Type: application/json' \
--data-raw '{
  "detail-type": "surgical",
  "source": "scheduling.event",
  "detail": {
        "schedule": {
          "date": "5/15/2024",
          "time": "10:00 AM",
          "location": "Building 6",
          "duration": "120 mins"
        },
        "therapy": {
          "OT": "yes",
          "PT": "yes"
        },
        "follow-ups": [
          "5/25/2024", "6/10/2024", "9/10/2024"
        ],
        "medication": "Oxycodone 5 mg every 4 hours.",
        "team": {
          "surgeon": "Jane Someone",
          "assistant": "John Person"
        },
        "procedure": {
          "type": "Anterior Cruciate Ligament",
          "location": "left knee"
        }
  }
}'
```

You've successfully tested all three stages and learned how to automate validation of requests through existing events.  

## Cleanup
 
1. Delete the stack
    ```
    sam delete
    ```

# Next steps
Check out our resources on [event driven architectures](https://aws-samples.github.io/eda-on-aws/) and additional guides and samples on [Serverlessland.com](https://www.serverlessland.com)


Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
