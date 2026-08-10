#!/bin/bash
# Utility script to restart the OpenSearch Ingestion Pipeline
# Usage: sh ./RestartOSIPipeline.sh
# Requires: AWS_USER and AWS_REGION environment variables to be set

if [ -z "$AWS_USER" ] || [ -z "$AWS_REGION" ]; then
    echo "ERROR: Required environment variables are not set."
    echo "Please set: AWS_USER and AWS_REGION"
    echo ""
    echo "Example:"
    echo "  export AWS_USER=<your-iam-user>"
    echo "  export AWS_REGION=<your-region>"
    exit 1
fi

echo "Stopping OSI Pipeline..."
aws osis stop-pipeline --pipeline-name das-osi-pipeline --profile $AWS_USER --region $AWS_REGION --no-cli-pager

max_attempts=25
attempt_num=1
success=false
while [ $success = false ] && [ $attempt_num -le $max_attempts ]; do
    echo "Getting Status of OSI Pipeline"

    PIPELINE_STATUS=$(aws osis get-pipeline --pipeline-name das-osi-pipeline --profile $AWS_USER --region $AWS_REGION --no-cli-pager | jq -r '.Pipeline.Status')

    if [ "$PIPELINE_STATUS" == "STOPPED" ]; then
        echo "PIPELINE_STATUS=$PIPELINE_STATUS"
        echo "PIPELINE is stopped"
        success=true
    else
        echo "PIPELINE_STATUS=$PIPELINE_STATUS"
        echo "PIPELINE is being stopped. Sleeping for 1 minute and trying again..."
        sleep 60
        ((attempt_num++))
    fi
done
echo "Pipeline has stopped. Now will attempt to restart it."

aws osis start-pipeline --pipeline-name das-osi-pipeline --profile $AWS_USER --region $AWS_REGION --no-cli-pager

max_attempts=25
attempt_num=1
success=false
while [ $success = false ] && [ $attempt_num -le $max_attempts ]; do
    echo "Getting Status of OSI Pipeline"

    PIPELINE_STATUS=$(aws osis get-pipeline --pipeline-name das-osi-pipeline --profile $AWS_USER --region $AWS_REGION --no-cli-pager | jq -r '.Pipeline.Status')

    if [ "$PIPELINE_STATUS" == "ACTIVE" ]; then
        echo "PIPELINE_STATUS=$PIPELINE_STATUS"
        echo "PIPELINE is started"
        success=true
    else
        echo "PIPELINE_STATUS=$PIPELINE_STATUS"
        echo "PIPELINE is being started. Sleeping for 1 minute and trying again..."
        sleep 60
        ((attempt_num++))
    fi
done
echo "Pipeline has restarted."
