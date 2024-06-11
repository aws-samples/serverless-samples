"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

Sample signer using Requests.
"""

import typing
from urllib.parse import urlparse

from aws_sdk_signers import URI, AWSRequest, Field, Fields, SigV4Signer
from requests import PreparedRequest
from requests.auth import AuthBase

if typing.TYPE_CHECKING:
    from aws_sdk_signers import AWSCredentialIdentity, SigV4SigningProperties

SIGNING_HEADERS = (
    "Authorization",
    "Date",
    "X-Amz-Date",
    "X-Amz-Security-Token",
    "X-Amz-Content-SHA256",
)


class SigV4Auth(AuthBase):
    """Attaches SigV4Authentication to the given Request object."""

    def __init__(
        self,
        signing_properties: "SigV4SigningProperties",
        identity: "AWSCredentialIdentity",
    ):
        self._signing_properties = signing_properties
        self._identity = identity
        self._signer = SigV4Signer()

    def __eq__(self, other):
        return self.signing_properties == getattr(other, "signing_properties", None)

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        self.sign_request(r)
        return r

    def sign_request(self, r: PreparedRequest):
        request = self.convert_to_awsrequest(r)
        signed_request = self._signer.sign(
            signing_properties=self._signing_properties,
            request=request,
            identity=self._identity,
        )
        for header in SIGNING_HEADERS:
            if header in signed_request.fields:
                r.headers[header] = signed_request.fields[header].as_string()
        return r

    def convert_to_awsrequest(self, r: PreparedRequest) -> AWSRequest:
        url_parts = urlparse(r.url)
        uri = URI(
            scheme=url_parts.scheme,
            host=url_parts.hostname,
            port=url_parts.port,
            path=url_parts.path,
            query=url_parts.query,
            fragment=url_parts.fragment,
        )
        fields = Fields([Field(name=k, values=[v]) for k, v in r.headers.items()])
        return AWSRequest(
            destination=uri,
            method=r.method,
            body=r.body,
            fields=fields,
        )
