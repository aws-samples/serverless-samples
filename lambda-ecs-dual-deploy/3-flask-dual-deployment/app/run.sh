#!/bin/sh

echo "Starting dual deployment container..."

# AWS_LAMBDA_RUNTIME_API is a Lambda runtime environment variable
if [ -z ${AWS_LAMBDA_RUNTIME_API} ]; then 
    echo "Running NOT IN Lambda execution environment" 
    echo "Executing non-Lambda deployment specific initialization code ..."
    # ECS/EKS/etc.
    gunicorn --bind 0.0.0.0:8000 application:app
else 
    echo "Running IN Lambda execution environment" 
    echo "Executing Lambda deployment specific initialization code ..."
    gunicorn --bind 0.0.0.0:8000 --daemon application:app 
    # Start lambda runtime client
    /usr/local/bin/python -m awslambdaric lambda.handler
fi
