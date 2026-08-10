#!/usr/bin/env bash
# teardown.sh — Remove all deployed resources.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${PROJECT_DIR}/config.env"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "ERROR: config.env not found."
  exit 1
fi

source "${CONFIG_FILE}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  API Gateway mTLS Demo — Teardown                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  This will delete:"
echo "    - CloudFormation stack: ${STACK_NAME}"
echo "    - S3 bucket contents:   ${TRUSTSTORE_BUCKET}"
echo "    - S3 bucket:            ${TRUSTSTORE_BUCKET}"
echo ""
read -p "  Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "  Aborted."
  exit 0
fi

echo ""
echo "  [1/3] Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name "${STACK_NAME}" --region "${AWS_REGION}"
echo "        Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_NAME}" --region "${AWS_REGION}" || true
echo "        Done."

echo "  [2/3] Emptying S3 bucket..."
aws s3 rm "s3://${TRUSTSTORE_BUCKET}" --recursive --region "${AWS_REGION}" 2>/dev/null || true
echo "        Done."

echo "  [3/3] Deleting S3 bucket..."
# Delete all object versions (required for versioned buckets)
aws s3api list-object-versions --bucket "${TRUSTSTORE_BUCKET}" --region "${AWS_REGION}" \
  --query 'Versions[].{Key:Key,VersionId:VersionId}' --output json 2>/dev/null | \
  python3 -c "
import json, sys, subprocess
versions = json.load(sys.stdin)
if versions:
    for v in versions:
        subprocess.run(['aws', 's3api', 'delete-object',
            '--bucket', '${TRUSTSTORE_BUCKET}',
            '--key', v['Key'],
            '--version-id', v['VersionId'],
            '--region', '${AWS_REGION}'], check=False)
" 2>/dev/null || true

aws s3api delete-bucket --bucket "${TRUSTSTORE_BUCKET}" --region "${AWS_REGION}" 2>/dev/null || true
echo "        Done."

echo ""
echo "  Teardown complete. Local certs in ./certs/ were NOT removed."
echo "  To remove local certs: rm -rf ./certs/"
echo ""
