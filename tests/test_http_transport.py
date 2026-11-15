"""Tests for the streamable HTTP transport and its bearer token check."""

import pytest
from starlette.testclient import TestClient

from temporal_mcp.server import TemporalMCPServer

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-06-18",
}
TOOLS_LIST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


@pytest.fixture
def make_client():
    def _make(bearer_token=None):
        app = TemporalMCPServer().http_app(host="0.0.0.0", bearer_token=bearer_token)
        return TestClient(app)

    return _make


class TestWithoutToken:
    def test_lists_tools(self, make_client):
        with make_client() as client:
            resp = client.post("/mcp", json=TOOLS_LIST, headers=MCP_HEADERS)
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()["result"]["tools"]]
        assert "list_workflows" in names

    def test_healthz(self, make_client):
        with make_client() as client:
            assert client.get("/healthz").text == "ok"


class TestWithToken:
    def test_missing_token_rejected(self, make_client):
        with make_client("s3cret") as client:
            resp = client.post("/mcp", json=TOOLS_LIST, headers=MCP_HEADERS)
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_wrong_token_rejected(self, make_client):
        with make_client("s3cret") as client:
            resp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_HEADERS, "Authorization": "Bearer nope"})
        assert resp.status_code == 401

    def test_wrong_scheme_rejected(self, make_client):
        with make_client("s3cret") as client:
            resp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_HEADERS, "Authorization": "Basic s3cret"})
        assert resp.status_code == 401

    def test_correct_token_accepted(self, make_client):
        with make_client("s3cret") as client:
            resp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_HEADERS, "Authorization": "Bearer s3cret"})
        assert resp.status_code == 200

    def test_scheme_is_case_insensitive(self, make_client):
        with make_client("s3cret") as client:
            resp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_HEADERS, "Authorization": "bearer s3cret"})
        assert resp.status_code == 200

    def test_token_is_case_sensitive(self, make_client):
        with make_client("s3cret") as client:
            resp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_HEADERS, "Authorization": "Bearer S3CRET"})
        assert resp.status_code == 401

    def test_other_paths_rejected(self, make_client):
        with make_client("s3cret") as client:
            assert client.get("/anything").status_code == 401

    def test_healthz_needs_no_token(self, make_client):
        with make_client("s3cret") as client:
            assert client.get("/healthz").status_code == 200
