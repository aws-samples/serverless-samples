#!/bin/sh

echo "Starting lambda container image..."

gunicorn --bind 0.0.0.0:8000 --daemon application:app 
/usr/local/bin/python -m awslambdaric lambda.handler
