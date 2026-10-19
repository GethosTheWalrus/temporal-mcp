"""OAuth token management for authenticating to a codec server."""

import asyncio
import contextlib
import json
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

from temporal_mcp.http_util import open_without_redirects, require_http_url

EXPIRY_BUFFER_SECONDS = 30
MIN_POLL_INTERVAL_SECONDS = 5
SLOW_DOWN_INCREMENT_SECONDS = 5
RETRYABLE_POLL_ERRORS = frozenset({"authorization_pending", "slow_down", "http_error"})

_FRACTION = re.compile(r"\.(\d+)")


class AuthRequiredError(Exception):
    """Raised when no usable token exists and the user must log in."""


class _OAuthError(Exception):
    def __init__(self, code: str, description: str):
        super().__init__(f"{code}: {description}" if description else code)
        self.code = code


class CodecTokenProvider:
    """Provides access tokens, refreshing them and running the OAuth device authorization login.

    The authorization server must be Auth0-compatible: it needs to serve `/oauth/device/code`
    and `/oauth/token`, accept an `audience` parameter, and issue refresh tokens for the
    `offline_access` scope. Tokens are cached in a JSON file holding access_token, refresh_token,
    token_type and expires_at (RFC 3339).
    """

    def __init__(
        self,
        cache_path: str,
        login_url: str,
        client_id: str,
        audience: str,
        timeout: float = 30.0,
    ):
        """Initialize the provider.

        Args:
            cache_path: File the token is read from and written to
            login_url: Base URL of the OAuth authorization server
            client_id: OAuth client ID used for device-code and refresh grants
            audience: OAuth audience requested at login
            timeout: HTTP request timeout in seconds
        """
        self.cache_path = cache_path
        self.login_url = require_http_url(login_url, "OAuth URL")
        self.client_id = client_id
        self.audience = audience
        self.timeout = timeout
        # _lock guards the state below and is never held during network I/O, so the event loop can take it.
        # _refresh_lock serialises refreshes, because a refresh token that rotates must not be used twice.
        self._lock = threading.Lock()
        self._refresh_lock = threading.Lock()
        self._login_lock = asyncio.Lock()
        self._token: Optional[dict[str, Any]] = None
        self._rejected_refresh_token: Optional[str] = None
        self._last_error: Optional[str] = None
        self._pending: Optional[dict[str, Any]] = None
        self._login_task: Optional["asyncio.Task[None]"] = None

    def get_token(self) -> str:
        """Return a valid access token, refreshing it if needed. Blocking; call from a worker thread.

        Raises:
            AuthRequiredError: If no valid token exists and refreshing is not possible.
        """
        with self._refresh_lock:
            with self._lock:
                token = self._current_token()
                if self._is_valid(token):
                    return str(token["access_token"])  # type: ignore[index]
                refresh_token = self._usable_refresh_token(token)

            if refresh_token:
                try:
                    refreshed = self._refresh(refresh_token)
                except Exception as e:
                    with self._lock:
                        if isinstance(e, _OAuthError) and e.code == "invalid_grant":
                            self._rejected_refresh_token = refresh_token
                        self._last_error = f"token refresh failed: {e}"
                else:
                    with self._lock:
                        self._last_error = None
                        self._store(refreshed)
                    return str(refreshed["access_token"])

            with self._lock:
                detail = f" ({self._last_error})" if self._last_error else ""
            raise AuthRequiredError(f"Codec login required: call the codec_login tool and complete the login in a browser{detail}")

    def status(self) -> dict[str, Any]:
        """Describe the current authentication state without contacting the server."""
        with self._lock:
            token = self._current_token()
            pending = dict(self._pending) if self._pending else None
            last_error = self._last_error
            can_refresh = self._usable_refresh_token(token) is not None

        result: dict[str, Any] = {}
        if self._is_valid(token):
            result["status"] = "authenticated"
            result["expires_at"] = datetime.fromtimestamp(token["expires_at"], tz=timezone.utc).isoformat()  # type: ignore[index]
        elif pending is not None:
            result["status"] = "login_pending"
            result["verification_uri"] = pending["verification_uri"]
            result["verification_uri_complete"] = pending["verification_uri_complete"]
            result["user_code"] = pending["user_code"]
            result["expires_in_seconds"] = max(int(pending["deadline"] - time.time()), 0)
        else:
            result["status"] = "refresh_available" if can_refresh else "login_required"
        if last_error:
            result["last_error"] = last_error
        return result

    async def start_login(self) -> dict[str, Any]:
        """Start the device login, or report the one already in progress.

        Refreshes silently instead when a refresh token is available.

        Returns:
            Authentication state; when a login is pending it includes the URL and code the user must use.
        """
        async with self._login_lock:
            if self.status()["status"] == "refresh_available":
                with contextlib.suppress(AuthRequiredError):
                    await asyncio.to_thread(self.get_token)
            current = self.status()
            if current["status"] in ("authenticated", "login_pending"):
                return current

            response = await asyncio.to_thread(
                self._post_form,
                "/oauth/device/code",
                {"client_id": self.client_id, "scope": "openid profile user offline_access", "audience": self.audience},
            )
            try:
                pending = {
                    "device_code": response["device_code"],
                    "user_code": response["user_code"],
                    "verification_uri": response["verification_uri"],
                    "verification_uri_complete": response.get("verification_uri_complete", ""),
                    "deadline": time.time() + int(response["expires_in"]),
                    "interval": max(int(response.get("interval", 0)), MIN_POLL_INTERVAL_SECONDS),
                }
            except (KeyError, TypeError, ValueError) as e:
                raise _OAuthError("invalid_response", f"unexpected device code response: {e!r}") from e
            with self._lock:
                self._pending = pending
                self._last_error = None
            self._login_task = asyncio.create_task(self._poll_login(pending))
            return self.status()

    async def _poll_login(self, pending: dict[str, Any]) -> None:
        try:
            while time.time() < pending["deadline"]:
                await asyncio.sleep(pending["interval"])
                try:
                    response = await asyncio.to_thread(
                        self._post_form,
                        "/oauth/token",
                        {"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "device_code": pending["device_code"], "client_id": self.client_id},
                    )
                    token = self._token_from_response(response)
                except _OAuthError as e:
                    if e.code == "slow_down":
                        pending["interval"] += SLOW_DOWN_INCREMENT_SECONDS
                    if e.code in RETRYABLE_POLL_ERRORS:
                        continue
                    self._record_error(f"login failed: {e}")
                    return
                except OSError:
                    continue
                with self._lock:
                    self._store(token)
                return
            self._record_error("login expired before it was completed")
        except Exception as e:
            self._record_error(f"login failed: {e}")
        finally:
            with self._lock:
                if self._pending is pending:
                    self._pending = None

    def _record_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message

    def _current_token(self) -> Optional[dict[str, Any]]:
        """Return the newest known token, preferring the cache file when another process has updated it. Caller holds _lock."""
        loaded = self._load()
        if loaded and (self._token is None or loaded["expires_at"] > self._token["expires_at"]):
            self._token = loaded
        return self._token

    def _usable_refresh_token(self, token: Optional[dict[str, Any]]) -> Optional[str]:
        refresh_token = token.get("refresh_token") if token else None
        return refresh_token if refresh_token and refresh_token != self._rejected_refresh_token else None

    def _is_valid(self, token: Optional[dict[str, Any]]) -> bool:
        return bool(token and token.get("access_token") and token["expires_at"] - EXPIRY_BUFFER_SECONDS > time.time())

    def _refresh(self, refresh_token: str) -> dict[str, Any]:
        response = self._post_form(
            "/oauth/token",
            {"grant_type": "refresh_token", "client_id": self.client_id, "refresh_token": refresh_token},
        )
        token = self._token_from_response(response)
        token["refresh_token"] = token["refresh_token"] or refresh_token
        return token

    def _token_from_response(self, response: dict[str, Any]) -> dict[str, Any]:
        try:
            return {
                "access_token": response["access_token"],
                "refresh_token": response.get("refresh_token", ""),
                "token_type": response.get("token_type", "Bearer"),
                "expires_at": time.time() + int(response["expires_in"]),
            }
        except (KeyError, TypeError, ValueError) as e:
            raise _OAuthError("invalid_response", f"unexpected token response: {e!r}") from e

    def _post_form(self, path: str, form: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.login_url + path,
            data=urllib.parse.urlencode(form).encode(),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with open_without_redirects(request, self.timeout) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read())
            except ValueError:
                raise _OAuthError("http_error", f"HTTP {e.code}") from e
        if not isinstance(body, dict):
            raise _OAuthError("invalid_response", "response is not a JSON object")
        if body.get("error"):
            raise _OAuthError(body["error"], body.get("error_description", ""))
        return body

    def _load(self) -> Optional[dict[str, Any]]:
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {
                "access_token": raw.get("access_token", ""),
                "refresh_token": raw.get("refresh_token", ""),
                "token_type": raw.get("token_type", "Bearer"),
                "expires_at": _parse_timestamp(raw["expires_at"]),
            }
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    def _store(self, token: dict[str, Any]) -> None:
        """Keep the token in memory and persist it. A failed write must not discard a usable token. Caller holds _lock."""
        self._token = token
        try:
            self._save(token)
        except OSError as e:
            self._last_error = f"could not write token cache: {e}"

    def _save(self, token: dict[str, Any]) -> None:
        directory = os.path.dirname(os.path.abspath(self.cache_path))
        os.makedirs(directory, exist_ok=True)
        serialized = {
            "access_token": token["access_token"],
            "refresh_token": token["refresh_token"],
            "token_type": token["token_type"],
            "expires_at": datetime.fromtimestamp(token["expires_at"], tz=timezone.utc).isoformat(),
        }
        # mkstemp creates the file with mode 0600; replacing is atomic, so a crash cannot leave a truncated cache.
        fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".token-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(serialized, f)
            os.replace(temp_path, self.cache_path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise


def _parse_timestamp(value: str) -> float:
    """Parse an RFC 3339 timestamp, including the forms Python 3.10's fromisoformat rejects (a trailing Z, nanoseconds)."""
    normalized = value.strip()
    if normalized[-1:] in ("Z", "z"):
        normalized = normalized[:-1] + "+00:00"
    normalized = _FRACTION.sub(lambda m: "." + m.group(1)[:6].ljust(6, "0"), normalized, count=1)
    return datetime.fromisoformat(normalized).timestamp()
