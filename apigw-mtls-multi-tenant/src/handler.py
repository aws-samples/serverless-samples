"""
Simple Lambda handler for the mTLS demo.
Returns request context including mTLS client cert info when available.
"""

import json


def lambda_handler(event, context):
    """Return 200 with mTLS client certificate details from the request context."""

    # Extract mTLS authentication context if present
    request_context = event.get("requestContext", {})
    auth = request_context.get("authentication", {})
    client_cert = auth.get("clientCert", {})

    body = {
        "message": "mTLS authentication successful",
        "clientCert": {
            "commonName": client_cert.get("subjectDN", "N/A"),
            "issuer": client_cert.get("issuerDN", "N/A"),
            "serialNumber": client_cert.get("serialNumber", "N/A"),
            "validity": {
                "notBefore": client_cert.get("validity", {}).get("notBefore", "N/A"),
                "notAfter": client_cert.get("validity", {}).get("notAfter", "N/A"),
            },
        },
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, indent=2),
    }
