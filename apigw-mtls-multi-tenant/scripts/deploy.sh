#!/usr/bin/env bash
# deploy.sh — End-to-end deployment: generate certs, upload truststore, deploy SAM stack.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERT_DIR="${PROJECT_DIR}/certs"
CONFIG_FILE="${PROJECT_DIR}/config.env"

# ─── Load configuration ────────────────────────────────────────────────────
if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "ERROR: config.env not found. Copy config.env.example and fill in your values."
  echo "  cp config.env.example config.env"
  exit 1
fi

source "${CONFIG_FILE}"

# Validate required vars
for var in DOMAIN_NAME HOSTED_ZONE_ID CERTIFICATE_ARN TRUSTSTORE_BUCKET STACK_NAME AWS_REGION; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: ${var} is not set in config.env"
    exit 1
  fi
done

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  API Gateway mTLS Full-Chain Truststore Demo — Deployment   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Domain:      ${DOMAIN_NAME}"
echo "  Region:      ${AWS_REGION}"
echo "  Stack:       ${STACK_NAME}"
echo "  Truststore:  s3://${TRUSTSTORE_BUCKET}/truststore.pem"
echo ""

# ─── Step 1: Generate certificates ─────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Generate PKI certificates"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ -f "${CERT_DIR}/truststore.pem" ]]; then
  echo "  Certificates already exist in ${CERT_DIR}. Skipping generation."
  echo "  (Delete ${CERT_DIR} to regenerate.)"
else
  bash "${SCRIPT_DIR}/generate-certs.sh" "${CERT_DIR}"
fi
echo ""

# ─── Step 2: Upload truststore to S3 ───────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Upload truststore to S3"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create bucket if it doesn't exist
if ! aws s3api head-bucket --bucket "${TRUSTSTORE_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
  echo "  Creating bucket: ${TRUSTSTORE_BUCKET}"
  if [[ "${AWS_REGION}" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "${TRUSTSTORE_BUCKET}" --region "${AWS_REGION}"
  else
    aws s3api create-bucket --bucket "${TRUSTSTORE_BUCKET}" --region "${AWS_REGION}" \
      --create-bucket-configuration LocationConstraint="${AWS_REGION}"
  fi
  aws s3api put-bucket-versioning --bucket "${TRUSTSTORE_BUCKET}" \
    --versioning-configuration Status=Enabled --region "${AWS_REGION}"
fi

echo "  Uploading truststore.pem..."
aws s3 cp "${CERT_DIR}/truststore.pem" "s3://${TRUSTSTORE_BUCKET}/truststore.pem" \
  --region "${AWS_REGION}"

# Get the S3 version ID (required for API Gateway mTLS with versioned buckets)
TRUSTSTORE_VERSION=$(aws s3api head-object --bucket "${TRUSTSTORE_BUCKET}" --key "truststore.pem" \
  --region "${AWS_REGION}" --query "VersionId" --output text)
echo "  Truststore version: ${TRUSTSTORE_VERSION}"
echo "  Done."
echo ""

# ─── Step 3: SAM build & deploy ────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: SAM build & deploy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "${PROJECT_DIR}"

echo "  Building..."
sam build --template-file template.yaml

echo "  Deploying..."
sam deploy \
  --stack-name "${STACK_NAME}" \
  --region "${AWS_REGION}" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "DomainName=${DOMAIN_NAME}" \
    "HostedZoneId=${HOSTED_ZONE_ID}" \
    "CertificateArn=${CERTIFICATE_ARN}" \
    "TruststoreBucket=${TRUSTSTORE_BUCKET}" \
    "TruststoreKey=truststore.pem" \
    "TruststoreVersion=${TRUSTSTORE_VERSION}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DEPLOYMENT COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  API Endpoint: https://${DOMAIN_NAME}/"
echo ""
echo "  NOTE: The custom domain may take a few minutes to become AVAILABLE."
echo "  Check status with:"
echo "    aws apigatewayv2 get-domain-name --domain-name ${DOMAIN_NAME} --region ${AWS_REGION}"
echo ""
echo "  Once ready, test with:"
echo "    bash scripts/test-mtls.sh"
echo ""
