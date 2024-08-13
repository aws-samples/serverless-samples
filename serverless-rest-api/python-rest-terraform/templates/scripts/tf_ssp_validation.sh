# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/bin/bash

# Accept Command Line Arguments
SKIPVALIDATIONFAILURE=$1
pyTest=$2
tfValidate=$3
tfFormat=$4
tfCheckov=$5
tfTfsec=$6
# -----------------------------

echo "### VALIDATION Overview ###"
echo "-------------------------"
echo "Skip Validation Errors on Failure : ${SKIPVALIDATIONFAILURE}"
echo "Python Unit Tests  : ${pyTest}"
echo "Terraform Validate : ${tfValidate}"
echo "Terraform Format   : ${tfFormat}"
echo "Terraform checkov  : ${tfCheckov}"
echo "Terraform tfsec    : ${tfTfsec}"
echo "------------------------"

if [[ ${pyTest} == "Y" ]]
then
    echo "## VALIDATION : Validating Python code Unit Tests ..."
    pip install -r ./src/lambda_layer/requirements.txt
    pip install -r ./tests/requirements.txt 
    python -m pytest tests/unit -v
fi
pyTestOutput=$?

terraform init -backend=false

if [[ ${tfValidate} == "Y" ]]
then
    echo "## VALIDATION : Validating Terraform code ..."
    terraform validate
fi
tfValidateOutput=$?

if [[ ${tfFormat} == "Y" ]]
then
    echo "## VALIDATION : Formatting Terraform code ..."
    terraform fmt -recursive
fi
tfFormatOutput=$?

if [[ ${tfCheckov} == "Y" ]]
then
    echo "## VALIDATION : Running checkov ..."
    #checkov -s -d .
    checkov -o junitxml --framework terraform --download-external-modules true -d ./ >checkov.xml
fi
tfCheckovOutput=$?

if [[ ${tfTfsec} == "Y" ]]
then
    echo "## VALIDATION : Running tfsec ..."
    #tfsec .
    tfsec ./ --format junit --out tfsec-junit.xml
fi
tfTfsecOutput=$?

echo "## VALIDATION Summary ##"
echo "------------------------"
echo "Python Unit Tests  : ${pyTestOutput}"
echo "Terraform Validate : ${tfValidateOutput}"
echo "Terraform Format   : ${tfFormatOutput}"
echo "Terraform checkov  : ${tfCheckovOutput}"
echo "Terraform tfsec    : ${tfTfsecOutput}"
echo "------------------------"
echo "Skip Validation Errors on Failure : ${SKIPVALIDATIONFAILURE}"
if [[ ${SKIPVALIDATIONFAILURE} == "Y" ]]
then
  #if SKIPVALIDATIONFAILURE is set as Y, then validation failures are skipped during execution
  echo "## VALIDATION : Skipping validation failure checks..."
elif (( $pyTestOutput == 0 && $tfValidateOutput == 0 && $tfFormatOutput == 0 && $tfCheckovOutput == 0  && $tfTfsecOutput == 0 ))
then
  echo "## VALIDATION : Checks Passed!!!"
else
  # When validation checks fails, build process is halted.
  echo "## ERROR : Validation Failed"
  exit 1;
fi