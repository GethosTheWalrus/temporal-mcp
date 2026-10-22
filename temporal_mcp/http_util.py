"""HTTP helpers for talking to the codec server and the OAuth server."""

import urllib.parse
import urllib.request
from typing import Any


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_opener = urllib.request.build_opener(_NoRedirectHandler)


def open_without_redirects(request: urllib.request.Request, timeout: float) -> Any:
    """Open a request without following redirects, so credentials are never forwarded to another host."""
    return _opener.open(request, timeout=timeout)


def require_http_url(url: str, name: str) -> str:
    """Return the URL without a trailing slash, rejecting anything but http(s) URLs with a host.

    urllib also opens file: and ftp: URLs, and a URL without a host fails later
    with an obscure error.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"{name} must be an http(s) URL with a host")
    return url.rstrip("/")
