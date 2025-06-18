#!/bin/bash

echo "Building the Lambda function..."
cd vtl-processor
mvn clean package -DskipTests
cd ..

echo "Starting local API with enhanced CORS configuration..."
sam local start-api --port 3000 --skip-pull-image
