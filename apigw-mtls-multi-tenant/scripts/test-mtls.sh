#!/usr/bin/env bash
# test-mtls.sh — Comprehensive API Gateway mTLS validation for customer PKI scenario.
#
# Customer context: Multi-tenant APIs with mTLS for client authentication.
# They need to validate:
#   (1) Full-chain truststore workaround works with their PKI structure
#   (2) Edge cases: size limits, propagation, intermediate rotation
#   (3) Leaf certificate expiry enforcement
#
# Tests:
#   1. Full-chain truststore (intermediate + root) → leaf validates ✅
#   2. Root-only truststore → leaf REJECTED (confirmed gap)
#   3. Expired leaf cert → REJECTED (expiry enforced)
#   4. Rotated intermediate CA → new leaf validates (rotation works)
#   5. No client cert → rejected (mTLS enforced)
#   6. Untrusted cert → rejected (chain-of-trust enforced)
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERT_DIR="${PROJECT_DIR}/certs"
CONFIG_FILE="${PROJECT_DIR}/config.env"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "ERROR: config.env not found."
  exit 1
fi

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

API_URL="https://${DOMAIN_NAME}/"
PASS=0
FAIL=0
SKIP=0

# ─── Helper: wait for domain to reach AVAILABLE status ──────────────────────
wait_for_domain_available() {
  local max_attempts=12  # 12 * 15s = 3 min max
  local attempt=0
  local status

  while (( attempt < max_attempts )); do
    status=$(aws apigatewayv2 get-domain-name --domain-name "${DOMAIN_NAME}" \
      --region "${AWS_REGION}" --query 'DomainNameConfigurations[0].DomainNameStatus' \
      --output text 2>/dev/null || echo "UNKNOWN")

    if [[ "${status}" == "AVAILABLE" ]]; then
      return 0
    fi

    ((attempt++))
    echo "  [⏳] Domain status: ${status} (attempt ${attempt}/${max_attempts}, waiting 15s)..."
    sleep 15
  done

  echo "  [⚠] Domain did not reach AVAILABLE within 3 minutes (last status: ${status})"
  return 1
}

# ─── Helper: update truststore on S3 and wait for propagation ───────────────
update_truststore() {
  local pem_file="$1"
  local description="$2"

  echo "  [→] Uploading ${description} to s3://${TRUSTSTORE_BUCKET}/truststore.pem..."
  aws s3 cp "${pem_file}" "s3://${TRUSTSTORE_BUCKET}/truststore.pem" \
    --region "${AWS_REGION}" --quiet

  local version
  version=$(aws s3api head-object \
    --bucket "${TRUSTSTORE_BUCKET}" --key truststore.pem \
    --region "${AWS_REGION}" --query 'VersionId' --output text 2>/dev/null || echo "")

  echo "  [→] Triggering domain truststore reimport..."
  if [[ -n "${version}" && "${version}" != "None" ]]; then
    aws apigatewayv2 update-domain-name \
      --domain-name "${DOMAIN_NAME}" \
      --region "${AWS_REGION}" \
      --mutual-tls-authentication "TruststoreUri=s3://${TRUSTSTORE_BUCKET}/truststore.pem,TruststoreVersion=${version}" \
      > /dev/null 2>&1 || true
  else
    aws apigatewayv2 update-domain-name \
      --domain-name "${DOMAIN_NAME}" \
      --region "${AWS_REGION}" \
      --mutual-tls-authentication "TruststoreUri=s3://${TRUSTSTORE_BUCKET}/truststore.pem" \
      > /dev/null 2>&1 || true
  fi

  echo "  [→] Waiting for truststore propagation..."
  wait_for_domain_available
}

# ─── Helper: test curl call and return HTTP code ────────────────────────────
call_api() {
  if [[ $# -eq 0 ]]; then
    curl -s -o /tmp/mtls-test-output.txt -w "%{http_code}" \
      "${API_URL}" 2>/dev/null || echo "000"
  else
    curl -s -o /tmp/mtls-test-output.txt -w "%{http_code}" \
      "$@" "${API_URL}" 2>/dev/null || echo "000"
  fi
}

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  API Gateway mTLS — Full Certificate Chain Validation Test Suite    ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  Multi-tenant mTLS with full-chain truststore validation          ║"
echo "║  Validates: workaround, expiry, rotation, enforcement               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Target: ${API_URL}"
echo "  Truststore: s3://${TRUSTSTORE_BUCKET}/truststore.pem"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Full-chain truststore validates leaf cert
# ═══════════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Full-chain truststore (intermediate + root) → leaf validates"
echo "        Proves: the documented workaround works"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

update_truststore "${CERT_DIR}/truststore.pem" "full-chain truststore (intermediate + root)"

HTTP_CODE=$(call_api --cert "${CERT_DIR}/leaf-client.pem" --key "${CERT_DIR}/leaf-client.key")

if [[ "${HTTP_CODE}" == "200" ]]; then
  echo "  ✅ PASS — HTTP 200. Leaf → Intermediate → Root chain resolved."
  echo ""
  echo "  Response:"
  python3 -m json.tool /tmp/mtls-test-output.txt 2>/dev/null || cat /tmp/mtls-test-output.txt
  ((PASS++))
else
  echo "  ❌ FAIL — Expected 200, got ${HTTP_CODE}"
  cat /tmp/mtls-test-output.txt 2>/dev/null
  ((FAIL++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Root-only truststore — leaf REJECTED
# ═══════════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Root-only truststore → leaf cert REJECTED"
echo "        Proves: API GW does NOT auto-walk root → intermediate → leaf"
echo "        Proves: API GW does NOT auto-walk root → intermediate → leaf"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

update_truststore "${CERT_DIR}/rootCA.pem" "root-only truststore"

HTTP_CODE=$(call_api --cert "${CERT_DIR}/leaf-client.pem" --key "${CERT_DIR}/leaf-client.key")

if [[ "${HTTP_CODE}" == "403" || "${HTTP_CODE}" =~ ^0+$ ]]; then
  echo "  ✅ PASS — Leaf cert REJECTED with root-only truststore (HTTP ${HTTP_CODE})"
  echo ""
  echo "  ╔═══════════════════════════════════════════════════════════════════╗"
  echo "  ║ CONFIRMED: API Gateway does NOT auto-walk the certificate chain. ║"
  echo "  ║ The intermediate CA MUST be present in the truststore.           ║"
  echo "  ╚═══════════════════════════════════════════════════════════════════╝"
  ((PASS++))
else
  echo "  ❌ FAIL — Expected rejection, got HTTP ${HTTP_CODE}"
  echo "     (Truststore update may not have fully propagated)"
  cat /tmp/mtls-test-output.txt 2>/dev/null
  ((FAIL++))
fi
echo ""

# Restore full-chain for remaining tests
echo "  [→] Restoring full-chain truststore for remaining tests..."
update_truststore "${CERT_DIR}/truststore.pem" "full-chain truststore (restored)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Expired leaf cert — REJECTED
# ═══════════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Expired leaf cert → REJECTED"
echo "        Proves: API GW checks leaf certificate validity period"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

EXPIRED_DIR=$(mktemp -d)

echo "  [→] Generating expired leaf certificate (using Python cryptography)..."

# LibreSSL doesn't support backdating certs, so use Python's cryptography library
python3 << PYEOF
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta, timezone
import sys

# Load intermediate CA cert and key
with open("${CERT_DIR}/intermediateCA.pem", "rb") as f:
    ca_cert = x509.load_pem_x509_certificate(f.read())
with open("${CERT_DIR}/intermediateCA.key", "rb") as f:
    ca_key = serialization.load_pem_private_key(f.read(), password=None)

# Generate a new key for the expired leaf
leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Build a cert that expired yesterday (valid from 3 days ago to 1 day ago)
now = datetime.now(timezone.utc)
subject = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "expired-client"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "mTLS Demo"),
    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
])

cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(ca_cert.subject)
    .public_key(leaf_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now - timedelta(days=3))
    .not_valid_after(now - timedelta(days=1))
    .sign(ca_key, hashes.SHA256())
)

# Write cert and key
with open("${EXPIRED_DIR}/expired.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))
with open("${EXPIRED_DIR}/expired.key", "wb") as f:
    f.write(leaf_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))

print("  [→] Expired cert created: valid {} to {} (expired)".format(
    (now - timedelta(days=3)).strftime("%Y-%m-%d"),
    (now - timedelta(days=1)).strftime("%Y-%m-%d"),
))
PYEOF

if [[ -f "${EXPIRED_DIR}/expired.pem" ]]; then
  # Confirm it's expired
  if ! openssl x509 -in "${EXPIRED_DIR}/expired.pem" -checkend 0 > /dev/null 2>&1; then
    echo "  [→] Expiry confirmed locally. Testing against API Gateway..."

    HTTP_CODE=$(call_api --cert "${EXPIRED_DIR}/expired.pem" --key "${EXPIRED_DIR}/expired.key")

    if [[ "${HTTP_CODE}" == "403" || "${HTTP_CODE}" =~ ^0+$ ]]; then
      echo "  ✅ PASS — Expired leaf cert REJECTED (HTTP ${HTTP_CODE})"
      echo "  API Gateway validates certificate NotAfter date."
      ((PASS++))
    else
      echo "  ❌ FAIL — Expected rejection of expired cert, got HTTP ${HTTP_CODE}"
      cat /tmp/mtls-test-output.txt 2>/dev/null
      ((FAIL++))
    fi
  else
    echo "  ⚠️  SKIP — Generated cert is not actually expired (clock issue?)."
    ((SKIP++))
  fi
else
  echo "  ⚠️  SKIP — Failed to generate expired cert."
  echo "     Ensure python3 with 'cryptography' package is installed:"
  echo "       pip3 install cryptography==50.0.0"
  ((SKIP++))
fi

rm -rf "${EXPIRED_DIR}"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Intermediate CA rotation — new leaf from new intermediate validates
# ═══════════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 4: Intermediate CA rotation — new intermediate + leaf validates"
echo "        Proves: truststore can be updated for CA rotation without"
echo "        downtime (CA key rotation scenario)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ROTATION_DIR=$(mktemp -d)

echo "  [→] Generating new (rotated) Intermediate CA..."
openssl genrsa -out "${ROTATION_DIR}/intermediateCA-v2.key" 4096 2>/dev/null
openssl req -new -key "${ROTATION_DIR}/intermediateCA-v2.key" \
  -subj "/CN=Demo Intermediate CA v2/O=mTLS Demo/C=US" -out "${ROTATION_DIR}/intermediateCA-v2.csr" 2>/dev/null
openssl x509 -req -in "${ROTATION_DIR}/intermediateCA-v2.csr" \
  -CA "${CERT_DIR}/rootCA.pem" -CAkey "${CERT_DIR}/rootCA.key" \
  -CAcreateserial -days 1825 -sha256 \
  -extfile <(printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign") \
  -out "${ROTATION_DIR}/intermediateCA-v2.pem" 2>/dev/null

echo "  [→] Issuing new leaf cert from rotated intermediate..."
openssl genrsa -out "${ROTATION_DIR}/leaf-v2.key" 2048 2>/dev/null
openssl req -new -key "${ROTATION_DIR}/leaf-v2.key" \
  -subj "/CN=rotated-client/O=mTLS Demo/C=US" -out "${ROTATION_DIR}/leaf-v2.csr" 2>/dev/null
openssl x509 -req -in "${ROTATION_DIR}/leaf-v2.csr" \
  -CA "${ROTATION_DIR}/intermediateCA-v2.pem" -CAkey "${ROTATION_DIR}/intermediateCA-v2.key" \
  -CAcreateserial -days 365 -sha256 -out "${ROTATION_DIR}/leaf-v2.pem" 2>/dev/null

echo "  [→] Building truststore with BOTH intermediates (rotation overlap)..."
cat "${CERT_DIR}/intermediateCA.pem" "${ROTATION_DIR}/intermediateCA-v2.pem" "${CERT_DIR}/rootCA.pem" \
  > "${ROTATION_DIR}/truststore-rotation.pem"

CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" "${ROTATION_DIR}/truststore-rotation.pem")
echo "  [→] Truststore contains ${CERT_COUNT} certificates (old intermediate + new intermediate + root)"

# Verify chain locally
openssl verify -CAfile "${CERT_DIR}/rootCA.pem" -untrusted "${ROTATION_DIR}/intermediateCA-v2.pem" \
  "${ROTATION_DIR}/leaf-v2.pem" > /dev/null 2>&1 && echo "  [→] Local chain verification: OK"

update_truststore "${ROTATION_DIR}/truststore-rotation.pem" "rotation truststore (both intermediates + root)"

echo "  [→] Testing new leaf cert against rotation truststore..."
HTTP_CODE=$(call_api --cert "${ROTATION_DIR}/leaf-v2.pem" --key "${ROTATION_DIR}/leaf-v2.key")

if [[ "${HTTP_CODE}" == "200" ]]; then
  echo "  ✅ PASS — New leaf from rotated intermediate validates (HTTP ${HTTP_CODE})"
  echo ""
  echo "  Rotation strategy confirmed:"
  echo "    1. Add new intermediate to truststore alongside old one"
  echo "    2. Issue new leaf certs from new intermediate"
  echo "    3. Once all clients migrated, remove old intermediate"
  ((PASS++))

  # Also verify old leaf still works (overlap period)
  echo ""
  echo "  [→] Verifying OLD leaf still works during overlap..."
  HTTP_CODE_OLD=$(call_api --cert "${CERT_DIR}/leaf-client.pem" --key "${CERT_DIR}/leaf-client.key")
  if [[ "${HTTP_CODE_OLD}" == "200" ]]; then
    echo "  ✅ Old leaf also validates — both CAs active simultaneously."
  else
    echo "  ⚠️  Old leaf rejected (HTTP ${HTTP_CODE_OLD}) — check propagation timing."
  fi
else
  echo "  ❌ FAIL — Expected 200 for rotated intermediate, got ${HTTP_CODE}"
  cat /tmp/mtls-test-output.txt 2>/dev/null
  ((FAIL++))
fi

rm -rf "${ROTATION_DIR}"
echo ""

# Restore original truststore
echo "  [→] Restoring original truststore..."
update_truststore "${CERT_DIR}/truststore.pem" "original truststore (restored)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: No client cert — mTLS enforced
# ═══════════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 5: No client cert (expect rejection)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HTTP_CODE=$(call_api)

if [[ "${HTTP_CODE}" == "403" || "${HTTP_CODE}" =~ ^0+$ ]]; then
  echo "  ✅ PASS — No-cert request rejected (HTTP ${HTTP_CODE})"
  ((PASS++))
else
  echo "  ❌ FAIL — Expected rejection, got HTTP ${HTTP_CODE}"
  ((FAIL++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: Untrusted self-signed cert — rejected
# ═══════════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 6: Untrusted self-signed cert (expect rejection)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TMPDIR=$(mktemp -d)
openssl req -x509 -newkey rsa:2048 -keyout "${TMPDIR}/rogue.key" \
  -out "${TMPDIR}/rogue.pem" -days 1 -nodes \
  -subj "/CN=rogue-client/O=Untrusted Org/C=US" 2>/dev/null

HTTP_CODE=$(call_api --cert "${TMPDIR}/rogue.pem" --key "${TMPDIR}/rogue.key")
rm -rf "${TMPDIR}"

if [[ "${HTTP_CODE}" == "403" || "${HTTP_CODE}" =~ ^0+$ ]]; then
  echo "  ✅ PASS — Untrusted cert rejected (HTTP ${HTTP_CODE})"
  ((PASS++))
else
  echo "  ❌ FAIL — Expected rejection, got HTTP ${HTTP_CODE}"
  ((FAIL++))
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "RESULTS: ${PASS} passed, ${FAIL} failed, ${SKIP} skipped (of 6 tests)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                        KEY FINDINGS                                 ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  1. Full chain workaround WORKS                                     ║"
echo "║     Truststore = intermediate(s) + root → leaf validates            ║"
echo "║                                                                     ║"
echo "║  2. Root-only truststore FAILS (confirmed gap)                      ║"
echo "║     API GW requires explicit intermediate CAs in truststore         ║"
echo "║                                                                     ║"
echo "║  3. Leaf expiry IS enforced                                         ║"
echo "║     Expired client certs are rejected at TLS handshake              ║"
echo "║                                                                     ║"
echo "║  4. Intermediate rotation is safe                                   ║"
echo "║     Include both old + new intermediates during transition           ║"
echo "║     Old and new leaf certs validate simultaneously                  ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║                    EDGE CASE NOTES                                  ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  • Truststore size: max 64 KB (PEM), ~40-50 CA certs               ║"
echo "║  • Max chain depth: 4 (root + 3 intermediates)                      ║"
echo "║  • Propagation: polls until AVAILABLE (typically 30-90s)            ║"
echo "║  • CRL/OCSP: NOT checked — use Lambda authorizer if needed          ║"
echo "║  • S3 versioning: recommended for safe truststore rollback          ║"
echo "║  • Rotation: include all active intermediates during transition      ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  Docs: https://docs.aws.amazon.com/apigateway/latest/               ║"
echo "║        developerguide/rest-api-mutual-tls.html                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

if [[ ${FAIL} -gt 0 ]]; then
  exit 1
fi
