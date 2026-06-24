"""Normalization and identifier helpers for smeli."""
from __future__ import annotations

import html
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote


def first(value: Any, default: str = "") -> Any:
    """Return the first element of a list-like value, or a default."""
    if isinstance(value, list) and value:
        return value[0]
    return default

def clean_doi(value: str | None) -> str | None:
    """Normalize common DOI representations to a bare DOI string."""
    if not value:
        return None

    doi = value.strip()
    prefixes = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    )

    lower = doi.lower()
    for prefix in prefixes:
        if lower.startswith(prefix):
            doi = doi[len(prefix):].strip()
            break

    doi = doi.strip().rstrip(".,;)]")
    if not doi:
        return None
    return doi

def looks_like_doi(value: str | None) -> bool:
    """Return True if text looks like a DOI or DOI URL."""
    doi = clean_doi(value)
    return bool(doi and re.match(r"^10\.\S+/\S+$", doi, re.IGNORECASE))

ORCID_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[0-9X]\b", re.IGNORECASE)

def extract_orcid(value: str | None) -> str | None:
    """Extract and normalize a bare ORCID iD from text/URL, if present."""
    if not value:
        return None

    text = value.strip()
    match = ORCID_RE.search(text)
    if not match:
        return None

    # ORCID check digits may be X; canonicalize that final character.
    orcid = match.group(0)
    return orcid[:-1] + orcid[-1].upper()

def looks_like_orcid(value: str | None) -> bool:
    """Return True if text contains an ORCID iD or ORCID URL."""
    return extract_orcid(value) is not None

def orcid_url(orcid: str | None) -> str | None:
    """Return the canonical ORCID URL for an ORCID iD-like value."""
    bare = extract_orcid(orcid)
    if not bare:
        return None
    return f"https://orcid.org/{bare}"

def quote_doi_for_path(doi: str) -> str:
    """
    Quote a DOI for APIs that place the DOI inside a URL path segment.

    The slash between the DOI prefix and suffix must be encoded for APIs like
    Crossref and DataCite path lookups.
    """
    return quote(doi, safe="")

def quote_doi_for_doi_org(doi: str) -> str:
    """
    Quote a DOI for doi.org URLs.

    doi.org handles ordinary DOI slashes naturally, so leave slashes unescaped
    while escaping spaces and other awkward characters.
    """
    return quote(doi, safe="/:")

def normalize_for_match(text: str | None) -> str:
    """Normalize text for forgiving-but-still-simple matching."""
    if not text:
        return ""

    # Unescape first so entities such as &eacute; become normal Unicode before
    # accent stripping. Otherwise "Caf&eacute;" would normalize to "café"
    # rather than "cafe".
    text = html.unescape(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def contains_normalized(haystack: str | None, needle: str | None) -> bool:
    """Case/punctuation/whitespace-insensitive substring check."""
    normalized_haystack = normalize_for_match(haystack)
    normalized_needle = normalize_for_match(needle)
    if not normalized_needle:
        return True
    return normalized_needle in normalized_haystack

def title_similarity(a: str | None, b: str | None) -> float:
    """Return a simple normalized-title similarity ratio."""
    na = normalize_for_match(a)
    nb = normalize_for_match(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()

def split_words(text: str | None) -> set[str]:
    """Return normalized word tokens, ignoring tiny stop words."""
    stop = {"a", "an", "and", "by", "for", "in", "of", "on", "the", "to", "with"}
    return {
        word
        for word in normalize_for_match(text).split()
        if len(word) > 2 and word not in stop
    }

def author_lastish_name(name: str) -> str:
    """Return a useful normalized author token for overlap checks."""
    raw = html.unescape(str(name or "")).strip()

    # Many metadata services use "Family, Given" while others use
    # "Given Family". Treat the part before a comma as the family-name-ish
    # token so "Starnini, Michele" overlaps with "Michele Starnini".
    if "," in raw:
        normalized_comma_family = normalize_for_match(raw.split(",", 1)[0])
        if normalized_comma_family:
            return normalized_comma_family.split()[-1]

    normalized = normalize_for_match(raw)
    if not normalized:
        return ""
    parts = normalized.split()
    return parts[-1]

def author_overlap(a: list[str], b: list[str]) -> bool:
    """Return True if two author lists share an apparent surname/name token."""
    a_names = {author_lastish_name(name) for name in a if author_lastish_name(name)}
    b_names = {author_lastish_name(name) for name in b if author_lastish_name(name)}
    return bool(a_names and b_names and a_names.intersection(b_names))

def get_year_from_crossref(data: dict[str, Any]) -> int | None:
    """Extract the best available publication year from Crossref metadata."""
    for field in ("published-print", "published-online", "published", "issued"):
        date_parts = data.get(field, {}).get("date-parts")
        if date_parts and date_parts[0]:
            return date_parts[0][0]
    return None

def get_year_from_date(value: str | None) -> int | None:
    """Extract a four-digit year from an ISO-ish date string."""
    if not value:
        return None
    match = re.search(r"\b(\d{4})\b", value)
    if not match:
        return None
    return int(match.group(1))

def extract_arxiv_id(value: str | None) -> str | None:
    """Extract a modern or old-style arXiv ID from text/URL, if present."""
    if not value:
        return None

    text = value.strip()

    # URL forms such as https://arxiv.org/abs/2507.11521v1 or /pdf/...
    match = re.search(
        r"arxiv\.org/(?:abs|pdf|html)/([^\s?#]+)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        arxiv_id = match.group(1).replace(".pdf", "")
        return arxiv_id.rstrip("/.,;)]")

    # Explicit arXiv: prefix.
    match = re.search(r"arxiv:\s*([^\s,;]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).rstrip("/.,;)]")

    # Modern IDs like 2507.11521 or 2507.11521v1.
    match = re.search(r"\b\d{4}\.\d{4,5}(?:v\d+)?\b", text)
    if match:
        return match.group(0)

    # Old-style IDs like cs/9901001 or math-ph/0303001v1.
    match = re.search(r"\b[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(0)

    return None

def base_arxiv_id(arxiv_id: str | None) -> str | None:
    """Strip an arXiv version suffix for deduplication."""
    if not arxiv_id:
        return None
    return re.sub(r"v\d+$", "", arxiv_id.strip(), flags=re.IGNORECASE)

def find_arxiv_id_in_mapping(mapping: dict[str, Any]) -> str | None:
    """Recursively look for an arXiv ID in a nested dict/list structure."""
    for value in mapping.values():
        if isinstance(value, str):
            found = extract_arxiv_id(value)
            if found:
                return found
        elif isinstance(value, dict):
            found = find_arxiv_id_in_mapping(value)
            if found:
                return found
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    found = extract_arxiv_id(item)
                    if found:
                        return found
                elif isinstance(item, dict):
                    found = find_arxiv_id_in_mapping(item)
                    if found:
                        return found
    return None

def make_arxiv_url(arxiv_id: str | None) -> str:
    """Return the canonical arXiv abstract URL for an ID."""
    return f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""

def maybe_int(value: Any) -> int | None:
    """Best-effort integer conversion."""
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
