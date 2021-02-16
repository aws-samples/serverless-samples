#!/bin/sh

echo "Starting container image..."

gunicorn --bind 0.0.0.0:8000 application:app
