"""Remote payload codec that delegates to a Temporal codec server."""

import asyncio
import json
import urllib.request
from dataclasses import dataclass
from typing import Optional, Sequence

from google.protobuf.json_format import MessageToDict, ParseDict
from temporalio.api.common.v1 import Payload, Payloads
from temporalio.converter import PayloadCodec

from temporal_mcp.http_util import open_without_redirects, require_http_url


@dataclass(frozen=True)
class CodecSettings:
    """How to reach a codec server.

    Attributes:
        endpoint: Base URL of the codec server
        auth: Full Authorization header value, e.g. "Bearer <token>"
    """

    endpoint: str
    auth: Optional[str] = None

    def __post_init__(self) -> None:
        require_http_url(self.endpoint, "Codec endpoint")

    def for_namespace(self, namespace: str) -> "RemoteCodec":
        """Build a codec that sends the given namespace, which codec servers use to select keys."""
        return RemoteCodec(self.endpoint, namespace, self.auth)


class RemoteCodec(PayloadCodec):
    """Encodes and decodes payloads through a codec server's /encode and /decode endpoints."""

    def __init__(
        self,
        endpoint: str,
        namespace: str,
        auth: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize the remote codec.

        Args:
            endpoint: Base URL of the codec server
            namespace: Namespace sent in the X-Namespace header
            auth: Full Authorization header value, e.g. "Bearer <token>"
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint.rstrip("/")
        self.namespace = namespace
        self.auth = auth
        self.timeout = timeout

    async def encode(self, payloads: Sequence[Payload]) -> list[Payload]:
        return await self._call("encode", payloads)

    async def decode(self, payloads: Sequence[Payload]) -> list[Payload]:
        return await self._call("decode", payloads)

    async def _call(self, operation: str, payloads: Sequence[Payload]) -> list[Payload]:
        if not payloads:
            return []
        body = json.dumps(MessageToDict(Payloads(payloads=payloads))).encode()
        response = await asyncio.to_thread(self._post, operation, body)
        result = list(ParseDict(response, Payloads()).payloads)
        if len(result) != len(payloads):
            raise ValueError(f"Codec server returned {len(result)} payloads for {len(payloads)} sent to /{operation}")
        return result

    def _post(self, operation: str, body: bytes) -> dict:
        request = urllib.request.Request(
            f"{self.endpoint}/{operation}",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "X-Namespace": self.namespace},
        )
        if self.auth:
            request.add_header("Authorization", self.auth)
        with open_without_redirects(request, self.timeout) as response:
            decoded: dict = json.loads(response.read())
        return decoded
