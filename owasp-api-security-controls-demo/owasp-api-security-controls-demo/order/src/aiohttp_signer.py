"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

Sample signer using aiohttp.
"""

import typing
from collections.abc import Mapping
from urllib.parse import urlparse

from aws_sdk_signers import URI, AsyncSigV4Signer, AWSRequest, Field, Fields

if typing.TYPE_CHECKING:
    from aws_sdk_signers import AWSCredentialIdentity, SigV4SigningProperties

SIGNING_HEADERS = (
    "Authorization",
    "Date",
    "X-Amz-Date",
    "X-Amz-Security-Token",
    "X-Amz-Content-SHA256",
)


class SigV4Signer:
    """Minimal Signer implementation to be used with AIOHTTP."""

    def __init__(
        self,
        signing_properties: "SigV4SigningProperties",
        identity: "AWSCredentialIdentity",
    ):
        self._signing_properties = signing_properties
        self._identity = identity
        self._signer = AsyncSigV4Signer()

    async def generate_signature(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: typing.AsyncIterable[bytes] | None,
    ) -> Mapping[str, str]:
        """Generate signature headers for applying to request."""
        url_parts = urlparse(url)
        uri = URI(
            scheme=url_parts.scheme,
            host=url_parts.hostname,
            port=url_parts.port,
            path=url_parts.path,
            query=url_parts.query,
            fragment=url_parts.fragment,
        )
        fields = Fields([Field(name=k, values=[v]) for k, v in headers.items()])
        awsrequest = AWSRequest(
            destination=uri,
            method=method,
            body=body,
            fields=fields,
        )
        signed_request = await self._signer.sign(
            signing_properties=self._signing_properties,
            request=awsrequest,
            identity=self._identity,
        )
        return {
            header: signed_request.fields[header].as_string()
            for header in SIGNING_HEADERS
            if header in signed_request.fields
        }
