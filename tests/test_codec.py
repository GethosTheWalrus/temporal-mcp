"""Tests for the remote codec and its data converter wiring."""

import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from google.protobuf.json_format import MessageToDict, ParseDict
from temporalio.api.common.v1 import Payload, Payloads
from temporalio.converter import DataConverter, DefaultFailureConverterWithEncodedAttributes

from temporal_mcp.client import TemporalClientManager
from temporal_mcp.codec import CodecSettings, RemoteCodec


def _serve(handler_class):
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def codec_server():
    """A codec server that reverses payload data, with switches for misbehaviour."""
    state = {"requests": [], "redirect_to": None, "drop_payloads": False}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append({"path": self.path, "headers": dict(self.headers), "body": body})
            if state["redirect_to"]:
                self.send_response(302)
                self.send_header("Location", state["redirect_to"])
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            payloads = [] if state["drop_payloads"] else [Payload(metadata=p.metadata, data=p.data[::-1]) for p in ParseDict(body, Payloads()).payloads]
            response = json.dumps(MessageToDict(Payloads(payloads=payloads))).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, *args):
            pass

    server = _serve(Handler)
    yield f"http://127.0.0.1:{server.server_port}", state
    server.shutdown()


class TestRemoteCodec:
    @pytest.mark.asyncio
    async def test_decode_posts_to_decode_with_namespace_and_auth(self, codec_server):
        endpoint, state = codec_server
        codec = RemoteCodec(endpoint + "/", namespace="ns.acct", auth="Bearer static")

        decoded = await codec.decode([Payload(metadata={"encoding": b"json/plain"}, data=b"cba")])

        assert [p.data for p in decoded] == [b"abc"]
        assert decoded[0].metadata["encoding"] == b"json/plain"
        assert state["requests"][0]["path"] == "/decode"
        assert state["requests"][0]["headers"]["X-Namespace"] == "ns.acct"
        assert state["requests"][0]["headers"]["Authorization"] == "Bearer static"

    @pytest.mark.asyncio
    async def test_encode_posts_to_encode_without_auth_when_none_configured(self, codec_server):
        endpoint, state = codec_server

        await RemoteCodec(endpoint, namespace="ns").encode([Payload(data=b"abc")])

        assert state["requests"][0]["path"] == "/encode"
        assert "Authorization" not in state["requests"][0]["headers"]

    @pytest.mark.asyncio
    async def test_empty_payloads_skip_request(self, codec_server):
        endpoint, state = codec_server

        assert await RemoteCodec(endpoint, namespace="ns").decode([]) == []
        assert state["requests"] == []

    @pytest.mark.asyncio
    async def test_redirect_is_not_followed_and_credentials_are_not_forwarded(self, codec_server):
        endpoint, state = codec_server
        forwarded = []

        class Target(BaseHTTPRequestHandler):
            def do_GET(self):
                forwarded.append(dict(self.headers))
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            do_POST = do_GET

            def log_message(self, *args):
                pass

        target = _serve(Target)
        state["redirect_to"] = f"http://127.0.0.1:{target.server_port}/steal"

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            await RemoteCodec(endpoint, namespace="ns", auth="Bearer SECRET").decode([Payload(data=b"x")])
        target.shutdown()

        assert exc_info.value.code == 302
        assert forwarded == []

    @pytest.mark.asyncio
    async def test_response_with_wrong_payload_count_is_rejected(self, codec_server):
        endpoint, state = codec_server
        state["drop_payloads"] = True

        with pytest.raises(ValueError, match="0 payloads for 1"):
            await RemoteCodec(endpoint, namespace="ns").decode([Payload(data=b"x")])


class TestCodecSettings:
    @pytest.mark.parametrize("endpoint", ["file:///etc/passwd", "ftp://codec.example", "codec.example"])
    def test_non_http_endpoint_is_rejected(self, endpoint):
        with pytest.raises(ValueError, match="http"):
            CodecSettings(endpoint=endpoint)

    def test_for_namespace_builds_a_codec_with_that_namespace(self):
        codec = CodecSettings(endpoint="https://codec.example/", auth="Bearer t").for_namespace("payments")

        assert (codec.endpoint, codec.namespace, codec.auth) == ("https://codec.example", "payments", "Bearer t")


class TestBuildDataConverter:
    def test_default_converter_without_codec(self):
        assert TemporalClientManager()._build_data_converter("default") is DataConverter.default

    def test_remote_codec_and_encoded_failure_converter_with_codec(self):
        converter = TemporalClientManager(namespace="ns.acct", codec=CodecSettings(endpoint="https://codec.example"))._build_data_converter("ns.acct")

        assert isinstance(converter.payload_codec, RemoteCodec)
        assert converter.payload_codec.endpoint == "https://codec.example"
        assert converter.payload_codec.namespace == "ns.acct"
        assert converter.failure_converter_class is DefaultFailureConverterWithEncodedAttributes
