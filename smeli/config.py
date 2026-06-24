"""Configuration for smeli."""
from __future__ import annotations

__all__: list[str] = []


import os

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:  # pragma: no cover - tiny optional dependency guard
    def _load_dotenv(*args, **kwargs):
        return False

_load_dotenv()

_DEFAULT_TIMEOUT = 20
_MAX_CANDIDATES_PER_SOURCE = 50
_MAX_DISPLAY_CANDIDATES = 30

_CONTACT_EMAIL = os.getenv("DOI_EMAIL") or os.getenv("DOI_PLAY_EMAIL", "")
_OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")

if _CONTACT_EMAIL:
    _USER_AGENT = f"smeli/0.1 (mailto:{_CONTACT_EMAIL})"
else:
    _USER_AGENT = "smeli/0.1"

_DEFAULT_HEADERS = {
    "User-Agent": _USER_AGENT,
}



