from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

HTTPS_PROVIDER = "http"
OFFLINE_PROVIDER = "offline"


class WebSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class WebResult:
    title: str
    url: str
    snippet: str


def websearch_provider() -> str:
    return os.environ.get("WEBSEARCH_PROVIDER", OFFLINE_PROVIDER)


def search_web(
    query: str,
    *,
    endpoint: str | None = None,
    timeout: float = 30.0,
) -> dict:
    """Registry-granted live web search (BEAD 7).

    Offline by default: without ``WEBSEARCH_PROVIDER=http`` and ``WEBSEARCH_ENDPOINT``
    the tool returns an explicit `unavailable` note instead of inventing data.
    """
    provider = websearch_provider()
    if provider == OFFLINE_PROVIDER:
        return {
            "status": "unavailable",
            "note": "websearch disabled: set WEBSEARCH_PROVIDER=http plus WEBSEARCH_ENDPOINT",
            "query": query,
            "items": [],
        }
    if provider == HTTPS_PROVIDER:
        url = endpoint or os.environ.get("WEBSEARCH_ENDPOINT")
        if not url:
            raise WebSearchError("WEBSEARCH_PROVIDER=http requires WEBSEARCH_ENDPOINT")
        body = json.dumps({"query": query, "count": 8}).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise WebSearchError(f"websearch request failed: {exc}") from exc
        items = [WebResult(**item) for item in payload.get("items", [])]
        return {"status": "ok", "query": query, "items": [item.__dict__ for item in items]}
    raise WebSearchError(f"unknown WEBSEARCH_PROVIDER: {provider!r}")


def fetch_page(url: str, *, timeout: float | None = None, max_chars: int = 8000) -> dict:
    """Registry-granted web fetch (BEAD 7). Returns a plain-text snapshot, truncated."""
    timeout = timeout or float(os.environ.get("HTTP_FETCH_TIMEOUT", "30"))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (OSError, ValueError) as exc:
        raise WebSearchError(f"webfetch failed for {url}: {exc}") from exc
    text = _to_text(raw)
    truncated = len(text) > max_chars
    return {
        "status": "ok",
        "url": url,
        "content": text[:max_chars],
        "chars": len(text),
        "truncated": truncated,
    }


def _to_text(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\\1>", " ", raw)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return html.unescape(re.sub(r"[ \t]+", " ", text)).strip()


def websearch_handler(query: str | None = None, **kwargs) -> dict:
    if not query or not query.strip():
        return {"status": "unavailable", "note": "empty query", "items": []}
    return search_web(query.strip())


def webfetch_handler(url: str | None = None, **kwargs) -> dict:
    if not url or not url.strip():
        return {"status": "unavailable", "note": "empty url"}
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return {"status": "unavailable", "note": f"scheme not allowed: {parsed.scheme}"}
    return fetch_page(url.strip())


_HANDLERS: dict[str, Callable] = {
    "websearch": websearch_handler,
    "webfetch": webfetch_handler,
}


def granted_tools(definition) -> dict[str, Callable]:
    """Return the web tools a definition was explicitly granted (BEAD 7 boundary)."""
    allowed = set(definition.allowed_tools or ())
    return {name: handler for name, handler in _HANDLERS.items() if name in allowed} if allowed else {}