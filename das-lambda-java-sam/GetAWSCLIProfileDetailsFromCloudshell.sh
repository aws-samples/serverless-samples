# Creating script for getting AWS Keys needed to set-up CLI profile on local machine
#!/bin/bash

# =============================================================================
# SECURITY NOTICE (sample / workshop helper - NON-PRODUCTION)
# This script prints long-lived AWS access keys to the console so you can copy
# them into a CLI profile on another machine. Use only with a disposable
# sandbox account for this sample. Treat the output as secret, clear your
# terminal scrollback afterwards, and delete the keys when done. For real use,
# prefer short-lived credentials (IAM Identity Center / STS) over access keys.
# =============================================================================

AWS_ACCESS_KEY=$(aws configure get aws_access_key_id --profile $1)
echo $AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key --profile $1)
echo $AWS_SECRET_ACCESS_KEY
AWS_CLI_REGION=$(aws configure get region --profile $1)
echo $AWS_CLI_REGION