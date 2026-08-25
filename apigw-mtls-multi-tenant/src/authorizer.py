"""
Lambda Authorizer for multi-tenant mTLS.

Extracts the client certificate from the mTLS handshake, logs full cert details
to CloudWatch (demonstrating where revocation checks could be added), and maps
the certificate CN to a tenant identity.

Tenant mapping:
  CN=tenant-a  → Tenant A
  CN=tenant-b  → Tenant B
  (other valid certs)  → default tenant

This authorizer demonstrates:
  1. How to extract and inspect client certs in a Lambda authorizer
  2. Where to add CRL/OCSP revocation checks (not natively supported by API GW)
  3. Multi-tenant routing based on certificate identity
"""

import json
import logging
import urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Tenant mapping: CN → tenant config
TENANT_MAP = {
    "tenant-a": {
        "tenantId": "tenant-a",
        "tenantName": "Tenant A",
        "allowedPaths": ["/api", "/api/", "/"],
    },
    "tenant-b": {
        "tenantId": "tenant-b",
        "tenantName": "Tenant B",
        "allowedPaths": ["/api", "/api/", "/"],
    },
}


def lambda_handler(event, context):
    """
    REQUEST-type Lambda authorizer for HTTP API.
    Receives the full request context including mTLS client cert.
    """
    logger.info("=== mTLS Authorizer Invoked ===")
    request_context = event.get("requestContext", {})
    logger.info(f"Request: routeKey={event.get('routeKey', '')}, "
                f"path={event.get('rawPath', '/')}, "
                f"requestId={request_context.get('requestId', 'N/A')}")

    # Extract client certificate from request context
    request_context = event.get("requestContext", {})
    auth_context = request_context.get("authentication", {})
    client_cert = auth_context.get("clientCert", {})

    if not client_cert:
        logger.warning("No client certificate found in request context")
        return build_deny_response("No client certificate")

    # Log full certificate details (this is where revocation checks would go)
    subject_dn = client_cert.get("subjectDN", "")
    issuer_dn = client_cert.get("issuerDN", "")
    serial = client_cert.get("serialNumber", "")
    validity = client_cert.get("validity", {})

    logger.info("=== Client Certificate Details ===")
    logger.info(f"  Subject DN:    {subject_dn}")
    logger.info(f"  Issuer DN:     {issuer_dn}")
    logger.info(f"  Serial Number: {serial}")
    logger.info(f"  Not Before:    {validity.get('notBefore', 'N/A')}")
    logger.info(f"  Not After:     {validity.get('notAfter', 'N/A')}")
    logger.info("=================================")

    # ─── Revocation Check — NOT IMPLEMENTED (demo only) ───────────────────────
    # ⚠️  SECURITY: This demo does NOT perform certificate revocation checking.
    # A compromised client certificate will remain valid until expiry.
    #
    # In production, implement one or more of the following before proceeding:
    #   1. DynamoDB/Redis denylist: query a table of revoked serial numbers
    #   2. CRL check: download CRL from CA's distribution point, verify serial
    #   3. OCSP check: send request to responder URL from cert's AIA extension
    #
    # Example:
    #   if is_revoked(serial, issuer_dn):
    #       logger.warning(f"REVOKED certificate: serial={serial}")
    #       return build_deny_response("Certificate revoked")
    #
    # Without revocation checking, the only remediation for a compromised cert is:
    #   - Remove the issuing CA from the truststore (affects all certs from that CA)
    #   - Wait for natural cert expiry
    logger.info("[Revocation Check] NOT IMPLEMENTED — demo only")

    # Extract CN from subject DN
    cn = extract_cn(subject_dn)
    logger.info(f"  Extracted CN: {cn}")

    # Map CN to tenant
    tenant = TENANT_MAP.get(cn)
    if tenant:
        logger.info(f"  Tenant identified: {tenant['tenantName']} ({tenant['tenantId']})")
    else:
        logger.warning(f"  Unknown CN={cn} — not mapped to any tenant. DENIED.")
        return build_deny_response(f"Certificate CN '{cn}' not authorized")

    # Check path authorization
    route_key = event.get("routeKey", "")
    request_path = event.get("rawPath", "/")
    # Strip stage prefix if present (API GW includes /prod/ in rawPath)
    for prefix in ["/prod", "/staging", "/dev"]:
        if request_path.startswith(prefix):
            request_path = request_path[len(prefix):] or "/"
            break
    logger.info(f"  Request path: {request_path}")
    logger.info(f"  Allowed paths: {tenant['allowedPaths']}")

    # Enforce path-level access control per tenant
    if request_path not in tenant["allowedPaths"]:
        logger.warning(f"  Path {request_path} not in allowed paths for tenant {tenant['tenantId']}")
        return build_deny_response(f"Access to {request_path} not authorized for this tenant")

    # Build allow response with tenant context
    response = build_allow_response(tenant, subject_dn, issuer_dn, serial)
    logger.info(f"  Authorization: ALLOW")
    logger.info(f"  Response context: {json.dumps(response.get('context', {}))}")

    return response


def extract_cn(subject_dn):
    """Extract CN value from a subject DN string like 'CN=tenant-a-att,O=...'"""
    # Handle both formats: "CN=value,O=..." and "/CN=value/O=..."
    dn = subject_dn.replace("/", ",").strip(",")
    for part in dn.split(","):
        part = part.strip()
        if part.upper().startswith("CN="):
            return part[3:]
    return ""


def build_allow_response(tenant, subject_dn, issuer_dn, serial):
    """Build IAM policy allowing access with tenant context."""
    return {
        "isAuthorized": True,
        "context": {
            "tenantId": tenant["tenantId"],
            "tenantName": tenant["tenantName"],
            "certSubject": subject_dn,
            "certIssuer": issuer_dn,
            "certSerial": serial,
        },
    }


def build_deny_response(reason):
    """Build deny response."""
    logger.warning(f"  Authorization: DENY — {reason}")
    return {
        "isAuthorized": False,
        "context": {
            "reason": reason,
        },
    }
