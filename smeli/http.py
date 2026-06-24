"""HTTP helpers for smeli metadata sources."""
from __future__ import annotations

__all__: list[str] = []


from typing import Any

import requests

from .config import _CONTACT_EMAIL, _DEFAULT_HEADERS, _DEFAULT_TIMEOUT, _OPENALEX_API_KEY


def _fetch_response(url: str, *, source: str = "request", **kwargs) -> requests.Response | None:
    """Fetch a URL with shared headers, a timeout, and friendly errors.

    Pass quiet_statuses={...} for expected non-success statuses that should
    simply behave like a missing record rather than producing terminal noise.
    """
    headers = kwargs.pop("headers", {})
    quiet_statuses = set(kwargs.pop("quiet_statuses", ()))
    merged_headers = {**_DEFAULT_HEADERS, **headers}
    timeout = kwargs.pop("timeout", _DEFAULT_TIMEOUT)

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
            if response.status_code in quiet_statuses:
                return None
            print(f"{source} request failed: {response.status_code} {response.reason}")
        else:
            print(f"{source} request failed: {e}")
    except requests.Timeout:
        print(f"{source} request timed out after {timeout} seconds.")
    except requests.RequestException as e:
        print(f"{source} request failed: {e}")

    return None

def _fetch_json(url: str, *, source: str = "request", **kwargs) -> dict[str, Any] | None:
    """Fetch a URL and return parsed JSON, or None on failure."""
    response = _fetch_response(url, source=source, **kwargs)
    if response is None:
        return None

    try:
        return response.json()
    except ValueError:
        print(f"{source} returned a response, but it was not valid JSON.")
        return None

def _fetch_text(url: str, *, source: str = "request", **kwargs) -> str | None:
    """Fetch a URL and return text, or None on failure."""
    response = _fetch_response(url, source=source, **kwargs)
    if response is None:
        return None
    return response.text

def _crossref_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return Crossref query params, including mailto when available."""
    params: dict[str, Any] = {}
    if _CONTACT_EMAIL:
        params["mailto"] = _CONTACT_EMAIL
    if extra:
        params.update(extra)
    return params

def _openalex_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return OpenAlex query params, including an API key if configured."""
    params: dict[str, Any] = {}
    if _OPENALEX_API_KEY:
        params["api_key"] = _OPENALEX_API_KEY
    if extra:
        params.update(extra)
    return params
