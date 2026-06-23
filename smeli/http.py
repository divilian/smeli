"""HTTP helpers for smeli metadata sources."""
from __future__ import annotations

from typing import Any

import requests

from .config import CONTACT_EMAIL, DEFAULT_HEADERS, DEFAULT_TIMEOUT, OPENALEX_API_KEY


def fetch_response(url: str, *, source: str = "request", **kwargs) -> requests.Response | None:
    """Fetch a URL with shared headers, a timeout, and friendly errors."""
    headers = kwargs.pop("headers", {})
    merged_headers = {**DEFAULT_HEADERS, **headers}
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)

    try:
        response = requests.get(
            url,
            headers=merged_headers,
            timeout=timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response
    except requests.HTTPError as e:
        response = e.response
        if response is not None:
            print(f"{source} request failed: {response.status_code} {response.reason}")
        else:
            print(f"{source} request failed: {e}")
    except requests.Timeout:
        print(f"{source} request timed out after {timeout} seconds.")
    except requests.RequestException as e:
        print(f"{source} request failed: {e}")

    return None

def fetch_json(url: str, *, source: str = "request", **kwargs) -> dict[str, Any] | None:
    """Fetch a URL and return parsed JSON, or None on failure."""
    response = fetch_response(url, source=source, **kwargs)
    if response is None:
        return None

    try:
        return response.json()
    except ValueError:
        print(f"{source} returned a response, but it was not valid JSON.")
        return None

def fetch_text(url: str, *, source: str = "request", **kwargs) -> str | None:
    """Fetch a URL and return text, or None on failure."""
    response = fetch_response(url, source=source, **kwargs)
    if response is None:
        return None
    return response.text

def crossref_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return Crossref query params, including mailto when available."""
    params: dict[str, Any] = {}
    if CONTACT_EMAIL:
        params["mailto"] = CONTACT_EMAIL
    if extra:
        params.update(extra)
    return params

def openalex_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return OpenAlex query params, including an API key if configured."""
    params: dict[str, Any] = {}
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY
    if extra:
        params.update(extra)
    return params
