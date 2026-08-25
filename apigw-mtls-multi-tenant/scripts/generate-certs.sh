#!/usr/bin/env bash
# generate-certs.sh — Build a 3-tier PKI: Root CA → Intermediate CA → Leaf (client) cert
# Also assembles the truststore PEM (intermediate + root) for API Gateway mTLS.
set -euo pipefail

CERT_DIR="${1:-./certs}"
DAYS_ROOT=3650
DAYS_INTERMEDIATE=1825
DAYS_LEAF=365

echo "==> Generating certificates in: ${CERT_DIR}"
mkdir -p "${CERT_DIR}"
cd "${CERT_DIR}"

# ─── Root CA ────────────────────────────────────────────────────────────────
echo "[1/4] Generating Root CA..."
openssl genrsa -out rootCA.key 4096 2>/dev/null
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days ${DAYS_ROOT} \
  -subj "/CN=Demo Root CA/O=mTLS Demo/C=US" -out rootCA.pem

# ─── Intermediate CA (signed by Root) ───────────────────────────────────────
echo "[2/4] Generating Intermediate CA..."
openssl genrsa -out intermediateCA.key 4096 2>/dev/null
openssl req -new -key intermediateCA.key \
  -subj "/CN=Demo Intermediate CA/O=mTLS Demo/C=US" -out intermediateCA.csr
openssl x509 -req -in intermediateCA.csr -CA rootCA.pem -CAkey rootCA.key \
  -CAcreateserial -days ${DAYS_INTERMEDIATE} -sha256 \
  -extfile <(printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign") \
  -out intermediateCA.pem 2>/dev/null

# ─── Leaf / Client cert (signed by Intermediate) ───────────────────────────
echo "[3/6] Generating Leaf (client) certificate..."
openssl genrsa -out leaf-client.key 2048 2>/dev/null
openssl req -new -key leaf-client.key \
  -subj "/CN=demo-client/O=mTLS Demo/C=US" -out leaf-client.csr
openssl x509 -req -in leaf-client.csr -CA intermediateCA.pem -CAkey intermediateCA.key \
  -CAcreateserial -days ${DAYS_LEAF} -sha256 -out leaf-client.pem 2>/dev/null

# ─── Tenant A cert (signed by Intermediate) ─────────────────────────────────
echo "[4/6] Generating Tenant A client certificate..."
openssl genrsa -out tenant-a.key 2048 2>/dev/null
openssl req -new -key tenant-a.key \
  -subj "/CN=tenant-a/O=Tenant A/OU=API-Access/C=US" -out tenant-a.csr
openssl x509 -req -in tenant-a.csr -CA intermediateCA.pem -CAkey intermediateCA.key \
  -CAcreateserial -days ${DAYS_LEAF} -sha256 -out tenant-a.pem 2>/dev/null

# ─── Tenant B cert (signed by Intermediate) ─────────────────────────────────
echo "[5/6] Generating Tenant B client certificate..."
openssl genrsa -out tenant-b.key 2048 2>/dev/null
openssl req -new -key tenant-b.key \
  -subj "/CN=tenant-b/O=Tenant B/OU=API-Access/C=US" -out tenant-b.csr
openssl x509 -req -in tenant-b.csr -CA intermediateCA.pem -CAkey intermediateCA.key \
  -CAcreateserial -days ${DAYS_LEAF} -sha256 -out tenant-b.pem 2>/dev/null

# ─── Assemble Truststore (intermediate + root) ─────────────────────────────
echo "[6/6] Assembling truststore PEM (intermediate + root)..."
cat intermediateCA.pem rootCA.pem > truststore.pem

# ─── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "==> Certificate generation complete!"
echo "    Root CA:          ${CERT_DIR}/rootCA.pem"
echo "    Intermediate CA:  ${CERT_DIR}/intermediateCA.pem"
echo "    Client cert:      ${CERT_DIR}/leaf-client.pem"
echo "    Client key:       ${CERT_DIR}/leaf-client.key"
echo "    Tenant A cert:    ${CERT_DIR}/tenant-a.pem"
echo "    Tenant A key:     ${CERT_DIR}/tenant-a.key"
echo "    Tenant B cert:    ${CERT_DIR}/tenant-b.pem"
echo "    Tenant B key:     ${CERT_DIR}/tenant-b.key"
echo "    Truststore:       ${CERT_DIR}/truststore.pem"
echo ""
echo "    Truststore contains $(grep -c 'BEGIN CERTIFICATE' truststore.pem) certificate(s)"
echo ""

# Verify the chains
echo "==> Verifying chains:"
echo "    leaf-client → intermediate → root"
openssl verify -CAfile rootCA.pem -untrusted intermediateCA.pem leaf-client.pem
echo "    tenant-a → intermediate → root"
openssl verify -CAfile rootCA.pem -untrusted intermediateCA.pem tenant-a.pem
echo "    tenant-b → intermediate → root"
openssl verify -CAfile rootCA.pem -untrusted intermediateCA.pem tenant-b.pem
echo ""
