"""Configuration for smeli."""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - tiny optional dependency guard
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

DEFAULT_TIMEOUT = 20
MAX_CANDIDATES_PER_SOURCE = 50
MAX_DISPLAY_CANDIDATES = 30

CONTACT_EMAIL = os.getenv("DOI_EMAIL") or os.getenv("DOI_PLAY_EMAIL", "")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")

if CONTACT_EMAIL:
    USER_AGENT = f"smeli/0.1 (mailto:{CONTACT_EMAIL})"
else:
    USER_AGENT = "smeli/0.1"

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
}



