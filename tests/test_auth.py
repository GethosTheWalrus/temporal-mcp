"""Tests for codec token management and the codec auth tools."""

import asyncio
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import pytest

from temporal_mcp import auth
from temporal_mcp.auth import AuthRequiredError, CodecTokenProvider
from temporal_mcp.codec import CodecSettings
from temporal_mcp.server import TemporalMCPServer

SUCCESS = (200, {"access_token": "fresh", "expires_in": 3600, "token_type": "Bearer"})


def _write_cache(path, access_token="cached", refresh_token="refresh-1", expires_in=3600):
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    path.write_text(json.dumps({"access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer", "expires_at": expires_at.isoformat()}))


def _provider(cache_path, login_url="https://login.example"):
    return CodecTokenProvider(str(cache_path), login_url=login_url, client_id="test-client", audience="https://test-audience")


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setattr(auth, "MIN_POLL_INTERVAL_SECONDS", 0.01)


@pytest.fixture
def oauth_server():
    state = {
        "requests": [],
        "times": [],
        "device_expires_in": 60,
        "device_response": None,
        "token_responses": [],
        "refresh_response": SUCCESS,
        "refresh_delay": 0,
        "redirect": False,
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            form = {k: v[0] for k, v in parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode()).items()}
            state["requests"].append({"path": self.path, "form": form})
            state["times"].append(time.monotonic())
            if state["redirect"]:
                self.send_response(302)
                # Fixed path: never build a Location header from test-controlled data.
                self.send_header("Location", "/redirected")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if self.path == "/oauth/device/code":
                status = 200
                body = state["device_response"] or {
                    "device_code": "dev-1",
                    "user_code": "ABCD-EFGH",
                    "verification_uri": "https://login.example/activate",
                    "verification_uri_complete": "https://login.example/activate?user_code=ABCD-EFGH",
                    "expires_in": state["device_expires_in"],
                    "interval": 0,
                }
            elif form["grant_type"] == "refresh_token":
                time.sleep(state["refresh_delay"])
                status, body = state["refresh_response"]
            else:
                status, body = state["token_responses"].pop(0)
            payload = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", state
    server.shutdown()


def _refresh_requests(state):
    return [r for r in state["requests"] if r["form"].get("grant_type") == "refresh_token"]


def _device_requests(state):
    return [r for r in state["requests"] if r["path"] == "/oauth/device/code"]


class TestGetToken:
    def test_valid_cached_token_is_returned_without_network(self, tmp_path, oauth_server):
        url, state = oauth_server
        cache = tmp_path / "token.json"
        _write_cache(cache)

        assert _provider(cache, url).get_token() == "cached"
        assert state["requests"] == []

    def test_expired_token_is_refreshed_and_persisted(self, tmp_path, oauth_server):
        url, state = oauth_server
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)

        assert _provider(cache, url).get_token() == "fresh"

        assert _refresh_requests(state)[0]["form"] == {"grant_type": "refresh_token", "client_id": "test-client", "refresh_token": "refresh-1"}
        saved = json.loads(cache.read_text())
        assert saved["access_token"] == "fresh"
        assert saved["refresh_token"] == "refresh-1"
        assert datetime.fromisoformat(saved["expires_at"]) > datetime.now(timezone.utc)

    def test_rotated_refresh_token_is_persisted(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["refresh_response"] = (200, {"access_token": "fresh", "refresh_token": "refresh-2", "expires_in": 3600})
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)

        _provider(cache, url).get_token()

        assert json.loads(cache.read_text())["refresh_token"] == "refresh-2"

    def test_cache_is_private_and_leaves_no_temporary_files(self, tmp_path, oauth_server):
        url, state = oauth_server
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)
        # Deliberately more permissive than 0600 so the test can prove the provider tightens it.
        cache.chmod(0o640)

        _provider(cache, url).get_token()

        assert os.stat(cache).st_mode & 0o777 == 0o600
        assert os.listdir(tmp_path) == ["token.json"]

    @pytest.mark.parametrize("expires_in, refreshes", [(10, True), (auth.EXPIRY_BUFFER_SECONDS + 30, False)])
    def test_token_is_refreshed_shortly_before_it_expires(self, tmp_path, oauth_server, expires_in, refreshes):
        url, state = oauth_server
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=expires_in)

        _provider(cache, url).get_token()

        assert bool(_refresh_requests(state)) is refreshes

    def test_failed_refresh_requires_login_and_names_the_tool(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["refresh_response"] = (403, {"error": "invalid_grant", "error_description": "Unknown or invalid refresh token."})
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)

        with pytest.raises(AuthRequiredError, match="codec_login.*invalid_grant"):
            _provider(cache, url).get_token()

    def test_rejected_refresh_token_is_not_retried(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["refresh_response"] = (403, {"error": "invalid_grant"})
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)
        provider = _provider(cache, url)

        for _ in range(3):
            with pytest.raises(AuthRequiredError):
                provider.get_token()

        assert len(_refresh_requests(state)) == 1
        assert provider.status()["status"] == "login_required"

    def test_new_refresh_token_in_the_cache_is_tried_after_a_rejection(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["refresh_response"] = (403, {"error": "invalid_grant"})
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)
        provider = _provider(cache, url)
        with pytest.raises(AuthRequiredError):
            provider.get_token()

        state["refresh_response"] = SUCCESS
        _write_cache(cache, refresh_token="refresh-2", expires_in=-10)

        assert provider.get_token() == "fresh"
        assert _refresh_requests(state)[-1]["form"]["refresh_token"] == "refresh-2"

    def test_transient_refresh_failure_is_retried_on_the_next_call(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["refresh_response"] = (502, "bad gateway")
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)
        provider = _provider(cache, url)

        with pytest.raises(AuthRequiredError, match="http_error"):
            provider.get_token()
        state["refresh_response"] = SUCCESS

        assert provider.get_token() == "fresh"
        assert len(_refresh_requests(state)) == 2
        assert "last_error" not in provider.status()

    def test_concurrent_callers_share_one_refresh(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["refresh_response"] = (200, {"access_token": "fresh", "refresh_token": "refresh-2", "expires_in": 3600})
        state["refresh_delay"] = 0.3
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)
        provider = _provider(cache, url)

        with ThreadPoolExecutor(max_workers=5) as pool:
            tokens = list(pool.map(lambda _: provider.get_token(), range(5)))

        assert tokens == ["fresh"] * 5
        assert len(_refresh_requests(state)) == 1

    def test_status_does_not_wait_for_a_refresh_in_flight(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["refresh_delay"] = 0.6
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)
        provider = _provider(cache, url)
        worker = threading.Thread(target=provider.get_token)
        worker.start()
        time.sleep(0.2)

        started = time.monotonic()
        status = provider.status()
        elapsed = time.monotonic() - started
        worker.join()

        assert elapsed < 0.2
        assert status["status"] == "refresh_available"

    def test_missing_cache_requires_login(self, tmp_path):
        with pytest.raises(AuthRequiredError, match="codec_login"):
            _provider(tmp_path / "missing.json").get_token()

    def test_token_written_by_another_process_is_picked_up(self, tmp_path):
        cache = tmp_path / "token.json"
        provider = _provider(cache)
        with pytest.raises(AuthRequiredError):
            provider.get_token()

        _write_cache(cache, access_token="from-other-process")

        assert provider.get_token() == "from-other-process"

    def test_failure_to_persist_does_not_discard_a_refreshed_token(self, tmp_path, oauth_server, monkeypatch):
        url, state = oauth_server
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)
        provider = _provider(cache, url)

        def disk_full(token):
            raise OSError("disk full")

        monkeypatch.setattr(provider, "_save", disk_full)

        assert provider.get_token() == "fresh"
        assert provider.get_token() == "fresh"
        assert len(_refresh_requests(state)) == 1
        assert "disk full" in provider.status()["last_error"]

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("2999-10-15T14:31:48.674402123+02:00", datetime(2999, 10, 15, 12, 31, 48, 674402, tzinfo=timezone.utc)),
            ("2999-10-15T12:31:48Z", datetime(2999, 10, 15, 12, 31, 48, tzinfo=timezone.utc)),
            ("2999-10-15T12:31:48.5+00:00", datetime(2999, 10, 15, 12, 31, 48, 500000, tzinfo=timezone.utc)),
            ("2999-10-15T12:31:48+00:00", datetime(2999, 10, 15, 12, 31, 48, tzinfo=timezone.utc)),
        ],
    )
    def test_rfc3339_timestamps_parse_on_every_supported_python(self, tmp_path, raw, expected):
        cache = tmp_path / "token.json"
        cache.write_text(json.dumps({"access_token": "go", "refresh_token": "r", "token_type": "Bearer", "expires_at": raw}))

        assert auth._parse_timestamp(raw) == expected.timestamp()
        assert _provider(cache).get_token() == "go"


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_returns_code_then_completes_in_background(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["token_responses"] = [
            (403, {"error": "authorization_pending"}),
            (200, {"access_token": "new", "refresh_token": "new-refresh", "expires_in": 3600, "token_type": "Bearer"}),
        ]
        cache = tmp_path / "token.json"
        provider = _provider(cache, url)

        started = await provider.start_login()

        assert started["status"] == "login_pending"
        assert started["user_code"] == "ABCD-EFGH"
        assert started["verification_uri_complete"].endswith("user_code=ABCD-EFGH")
        assert (await provider.start_login())["user_code"] == "ABCD-EFGH"
        assert len(_device_requests(state)) == 1
        assert _device_requests(state)[0]["form"]["client_id"] == "test-client"
        assert _device_requests(state)[0]["form"]["audience"] == "https://test-audience"

        await provider._login_task

        assert provider.status()["status"] == "authenticated"
        assert provider.get_token() == "new"
        assert json.loads(cache.read_text())["refresh_token"] == "new-refresh"
        token_requests = [r for r in state["requests"] if r["form"].get("grant_type") == "urn:ietf:params:oauth:grant-type:device_code"]
        assert {r["form"]["client_id"] for r in token_requests} == {"test-client"}
        assert {r["form"]["device_code"] for r in token_requests} == {"dev-1"}

    @pytest.mark.asyncio
    async def test_slow_down_makes_polling_slower(self, tmp_path, oauth_server, monkeypatch):
        url, state = oauth_server
        monkeypatch.setattr(auth, "SLOW_DOWN_INCREMENT_SECONDS", 0.3)
        state["token_responses"] = [(403, {"error": "slow_down"}), SUCCESS]
        provider = _provider(tmp_path / "token.json", url)

        await provider.start_login()
        await provider._login_task

        device_time, first_poll, second_poll = state["times"]
        assert first_poll - device_time < 0.2
        assert second_poll - first_poll >= 0.3

    @pytest.mark.asyncio
    async def test_polling_is_never_faster_than_the_minimum_interval(self, tmp_path, oauth_server, monkeypatch):
        url, state = oauth_server
        monkeypatch.setattr(auth, "MIN_POLL_INTERVAL_SECONDS", 0.25)
        state["token_responses"] = [SUCCESS]
        provider = _provider(tmp_path / "token.json", url)

        await provider.start_login()
        await provider._login_task

        device_time, poll_time = state["times"]
        assert poll_time - device_time >= 0.25

    @pytest.mark.asyncio
    async def test_denied_login_reports_the_error(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["token_responses"] = [(403, {"error": "access_denied", "error_description": "user said no"})]
        provider = _provider(tmp_path / "token.json", url)

        await provider.start_login()
        await provider._login_task

        status = provider.status()
        assert status["status"] == "login_required"
        assert "access_denied" in status["last_error"]

    @pytest.mark.asyncio
    async def test_login_stops_when_the_device_code_expires(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["device_expires_in"] = 0
        provider = _provider(tmp_path / "token.json", url)

        await provider.start_login()
        await asyncio.wait_for(provider._login_task, timeout=2)

        assert provider.status()["status"] == "login_required"
        assert "expired" in provider.status()["last_error"]
        assert [r for r in state["requests"] if r["path"] == "/oauth/token"] == []

    @pytest.mark.asyncio
    async def test_temporary_server_errors_do_not_end_the_login(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["token_responses"] = [(502, "bad gateway"), SUCCESS]
        provider = _provider(tmp_path / "token.json", url)

        await provider.start_login()
        await provider._login_task

        assert provider.status()["status"] == "authenticated"

    @pytest.mark.asyncio
    async def test_login_refreshes_silently_when_possible(self, tmp_path, oauth_server):
        url, state = oauth_server
        cache = tmp_path / "token.json"
        _write_cache(cache, expires_in=-10)

        result = await _provider(cache, url).start_login()

        assert result["status"] == "authenticated"
        assert _device_requests(state) == []

    @pytest.mark.asyncio
    async def test_concurrent_login_calls_start_one_device_flow(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["token_responses"] = [(403, {"error": "authorization_pending"})] * 3 + [SUCCESS]
        provider = _provider(tmp_path / "token.json", url)

        results = await asyncio.gather(*(provider.start_login() for _ in range(3)))
        await provider._login_task

        assert len(_device_requests(state)) == 1
        assert {r["user_code"] for r in results} == {"ABCD-EFGH"}
        assert provider.status()["status"] == "authenticated"

    @pytest.mark.asyncio
    async def test_error_from_a_failed_login_is_cleared_by_the_next_success(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["token_responses"] = [(403, {"error": "access_denied"})]
        provider = _provider(tmp_path / "token.json", url)
        await provider.start_login()
        await provider._login_task
        assert "last_error" in provider.status()

        state["token_responses"] = [SUCCESS]
        await provider.start_login()
        await provider._login_task

        assert provider.status()["status"] == "authenticated"
        assert "last_error" not in provider.status()

    @pytest.mark.asyncio
    async def test_unexpected_device_code_response_is_an_error(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["device_response"] = {"unexpected": True}

        with pytest.raises(Exception, match="invalid_response"):
            await _provider(tmp_path / "token.json", url).start_login()


class TestUrls:
    @pytest.mark.parametrize("login_url", ["file:///etc/passwd", "ftp://login.example", "login.example"])
    def test_non_http_oauth_url_is_rejected(self, tmp_path, login_url):
        with pytest.raises(ValueError, match="http"):
            _provider(tmp_path / "token.json", login_url)

    @pytest.mark.asyncio
    async def test_oauth_redirect_is_not_followed(self, tmp_path, oauth_server):
        url, state = oauth_server
        state["redirect"] = True

        with pytest.raises(Exception, match="HTTP 302"):
            await _provider(tmp_path / "token.json", url).start_login()

        assert [request["path"] for request in state["requests"]] == ["/oauth/device/code"]


class TestServerTools:
    def _server(self, tmp_path, login_url="https://login.example"):
        provider = _provider(tmp_path / "token.json", login_url)
        return TemporalMCPServer(codec=CodecSettings(endpoint="https://codec.example", token_provider=provider))

    @pytest.mark.asyncio
    async def test_auth_tools_listed_only_with_a_token_provider(self, tmp_path):
        with_provider = await self._server(tmp_path)._list_tools(None, None)
        static_auth = await TemporalMCPServer(codec=CodecSettings(endpoint="https://codec.example", auth="Bearer t"))._list_tools(None, None)
        without_codec = await TemporalMCPServer()._list_tools(None, None)

        names = {"codec_login", "codec_auth_status"}
        assert names <= {t.name for t in with_provider.tools}
        assert not names & {t.name for t in static_auth.tools}
        assert not names & {t.name for t in without_codec.tools}

    @pytest.mark.asyncio
    async def test_status_tool_works_without_a_temporal_connection(self, tmp_path):
        result = await self._server(tmp_path)._execute_tool("codec_auth_status", {})

        assert json.loads(result[0].text)["status"] == "login_required"

    @pytest.mark.asyncio
    async def test_login_failure_is_reported_as_a_tool_error(self, tmp_path):
        result = await self._server(tmp_path, login_url="http://127.0.0.1:1")._execute_tool("codec_login", {})

        assert result.model_dump(by_alias=True)["isError"] is True
        assert "codec_login" in result.content[0].text
