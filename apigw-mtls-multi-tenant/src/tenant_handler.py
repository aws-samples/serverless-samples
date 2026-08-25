"""
Multi-tenant Lambda handler for the mTLS demo.

All tenants hit the SAME endpoint (/api). The Lambda Authorizer identifies the
tenant from the client certificate CN and passes tenant context downstream.
This handler uses that context to return tenant-specific responses — demonstrating
cert-based routing without path differentiation.

Flow:
  Client cert (CN=tenant-a) → /api
  Client cert (CN=tenant-b) → /api  (same path!)
  Authorizer maps CN → tenantId → passed as context
  This handler reads tenantId from context → returns tenant-specific data
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Simulated tenant data (in production this would come from a database)
TENANT_DATA = {
    "tenant-a": {
        "name": "Tenant A",
        "region": "US-East",
        "apiVersion": "v2.1",
        "services": ["service-x", "service-y"],
        "rateLimit": 10000,
        "accountStatus": "active",
    },
    "tenant-b": {
        "name": "Tenant B",
        "region": "US-West",
        "apiVersion": "v3.0",
        "services": ["service-x", "service-y", "service-z"],
        "rateLimit": 15000,
        "accountStatus": "active",
    },
}


def lambda_handler(event, context):
    """Handle multi-tenant API requests — same path, different cert = different tenant."""
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    auth_context = authorizer.get("lambda", {})
    logger.info(f"Tenant handler invoked: path={event.get('rawPath', '/')}, "
                f"tenantId={auth_context.get('tenantId', 'unknown')}, "
                f"requestId={request_context.get('requestId', 'N/A')}")

    # Extract tenant context from authorizer (set by the Lambda Authorizer based on cert CN)
    tenant_id = auth_context.get("tenantId", "unknown")
    tenant_name = auth_context.get("tenantName", "Unknown")
    cert_subject = auth_context.get("certSubject", "N/A")
    cert_serial = auth_context.get("certSerial", "N/A")

    # Get tenant-specific data based on authorizer context (not path!)
    tenant_data = TENANT_DATA.get(tenant_id, {})

    body = {
        "message": f"Welcome, {tenant_name}!",
        "routing": {
            "method": "Certificate-based (same endpoint for all tenants)",
            "endpoint": "/api",
            "tenantDeterminedBy": "Client certificate CN → Lambda Authorizer → context",
        },
        "tenant": {
            "id": tenant_id,
            "name": tenant_name,
        },
        "authentication": {
            "method": "mTLS + Lambda Authorizer",
            "certSubject": cert_subject,
            "certSerial": cert_serial,
        },
        "tenantConfig": tenant_data if tenant_data else {
            "note": "No specific config — unrecognized tenant (default access)",
        },
    }

    logger.info(f"Responding to tenant: {tenant_id} ({tenant_name}) on shared /api endpoint")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, indent=2),
    }
