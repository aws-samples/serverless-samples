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
# Delete all object versions AND delete markers (required for versioned buckets)
echo "        Removing object versions..."
aws s3api list-object-versions --bucket "${TRUSTSTORE_BUCKET}" --region "${AWS_REGION}" \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null | \
  python3 -c "
import json, sys, subprocess
data = json.load(sys.stdin)
objects = data.get('Objects') or []
if objects:
    # Use batch delete for efficiency (max 1000 per call)
    for i in range(0, len(objects), 1000):
        batch = objects[i:i+1000]
        delete_payload = json.dumps({'Objects': batch, 'Quiet': True})
        subprocess.run(['aws', 's3api', 'delete-objects',
            '--bucket', '${TRUSTSTORE_BUCKET}',
            '--region', '${AWS_REGION}',
            '--delete', delete_payload], check=False, capture_output=True)
    print(f'        Deleted {len(objects)} version(s)')
" 2>/dev/null || true

echo "        Removing delete markers..."
aws s3api list-object-versions --bucket "${TRUSTSTORE_BUCKET}" --region "${AWS_REGION}" \
  --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null | \
  python3 -c "
import json, sys, subprocess
data = json.load(sys.stdin)
objects = data.get('Objects') or []
if objects:
    for i in range(0, len(objects), 1000):
        batch = objects[i:i+1000]
        delete_payload = json.dumps({'Objects': batch, 'Quiet': True})
        subprocess.run(['aws', 's3api', 'delete-objects',
            '--bucket', '${TRUSTSTORE_BUCKET}',
            '--region', '${AWS_REGION}',
            '--delete', delete_payload], check=False, capture_output=True)
    print(f'        Deleted {len(objects)} delete marker(s)')
" 2>/dev/null || true

aws s3api delete-bucket --bucket "${TRUSTSTORE_BUCKET}" --region "${AWS_REGION}" 2>/dev/null || true
echo "        Done."

echo ""
echo "  Teardown complete. Local certs in ./certs/ were NOT removed."
echo "  To remove local certs: rm -rf ./certs/"
echo ""
