# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Define global args
ARG APPLICATION_DIR="/home/app/"
ARG RUNTIME_VERSION="3.9"
ARG DISTRO_VERSION="3.12"
FROM python:${RUNTIME_VERSION}-alpine${DISTRO_VERSION} AS python-alpine

ARG APPLICATION_DIR
# Create application directory
RUN mkdir -p ${APPLICATION_DIR}
# Set working directory to application root directory
WORKDIR ${APPLICATION_DIR}
# Install application server
RUN pip install gunicorn 
# Copy application
COPY ./app/*.py ./app/*.sh ./app/requirements.txt ${APPLICATION_DIR}
RUN chmod +x ${APPLICATION_DIR}/*.sh
# Install application dependencies
RUN pip install -r ${APPLICATION_DIR}/requirements.txt --target ${APPLICATION_DIR}
ENTRYPOINT ["/home/app/run.sh"]
