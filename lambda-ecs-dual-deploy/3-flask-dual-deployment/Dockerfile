# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Define global args
ARG FUNCTION_DIR="/home/app/"
ARG RUNTIME_VERSION="3.9"
ARG DISTRO_VERSION="3.12"

# Stage 1 -bundle base image + runtime 
FROM python:${RUNTIME_VERSION}-alpine${DISTRO_VERSION} AS python-alpine
# Install GCC (Alpine uses musl but we compile and link dependencies with GCC)
RUN apk add --no-cache libstdc++
# Stage 2 -build function and dependencies
FROM python-alpine AS build-image
ARG FUNCTION_DIR
# Install aws-lambda-cpp build dependencies
RUN apk add --no-cache build-base libtool autoconf automake libexecinfo-dev make cmake libcurl 
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}
# Install Lambda Runtime Interface Client for Python
RUN python${RUNTIME_VERSION} -m pip install awslambdaric --target ${FUNCTION_DIR}

# Stage 3 - Install app server and copy app
FROM python-alpine
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}
# Install app server
RUN pip install gunicorn
# Copy in the built dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}
# Copy application and handler function
COPY ./app/*.py ./app/*.sh ./app/requirements.txt ${FUNCTION_DIR}
RUN chmod +x ${FUNCTION_DIR}/*.sh
# Install application dependencies
RUN pip install -r ${FUNCTION_DIR}/requirements.txt --target ${FUNCTION_DIR}
ENTRYPOINT ["/home/app/run.sh"]
