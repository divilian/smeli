"""Normalization and identifier helpers for Smeli.

This module contains small, side-effect-free helpers for recognizing and
normalizing scholarly identifiers. Public functions accept messy user input
where practical: bare identifiers, resolver URLs, common prefixes, and leading
or trailing whitespace.
"""
from __future__ import annotations

__all__ = [
    "clean_doi",
    "looks_like_doi",
    "extract_orcid",
    "looks_like_orcid",
    "orcid_url",
    "extract_arxiv_id",
    "base_arxiv_id",
    "make_arxiv_url",
]


import html
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote


def _first(value: Any, default: str = "") -> Any:
    """Return the first element of a list-like value, or a default."""
    if isinstance(value, list) and value:
        return value[0]
    return default

def clean_doi(value: str | None) -> str | None:
    """Normalize common DOI representations to a bare DOI string.

Args:
    value: A DOI-like string, DOI URL, ``doi:``-prefixed value, or ``None``.

Returns:
    The normalized bare DOI, preserving DOI case where present, or ``None`` if
    the input is empty or does not contain a valid-looking DOI.

Examples:
    ``clean_doi("https://doi.org/10.1126/science.1102081")`` returns
    ``"10.1126/science.1102081"``.
"""
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
    """Return whether text contains a valid-looking DOI.

Args:
    value: Text that may contain a bare DOI or DOI resolver URL.

Returns:
    ``True`` when :func:`clean_doi` can extract a DOI; otherwise ``False``.
"""
    doi = clean_doi(value)
    return bool(doi and re.match(r"^10\.\S+/\S+$", doi, re.IGNORECASE))

_ORCID_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[0-9X]\b", re.IGNORECASE)

def extract_orcid(value: Any | None) -> str | None:
    """Extract and normalize a bare ORCID iD from text, URL, or record.

Args:
    value: Text that may contain a bare ORCID iD or an ``orcid.org`` URL, or a
        nested candidate/source record that may contain an ORCID value.

Returns:
    The normalized bare ORCID iD, such as ``"0000-0002-0254-6627"``, or
    ``None`` when no ORCID-like identifier is present.
"""
    if not value:
        return None

    if isinstance(value, str):
        match = _ORCID_RE.search(value.strip())
        if not match:
            return None

        # ORCID check digits may be X; canonicalize that final character.
        orcid = match.group(0)
        return orcid[:-1] + orcid[-1].upper()

    if isinstance(value, dict):
        for item in value.values():
            orcid = extract_orcid(item)
            if orcid:
                return orcid
        return None

    if isinstance(value, (list, tuple, set)):
        for item in value:
            orcid = extract_orcid(item)
            if orcid:
                return orcid

    return None

def looks_like_orcid(value: str | None) -> bool:
    """Return whether text contains an ORCID iD or ORCID URL.

Args:
    value: Text that may contain an ORCID identifier.

Returns:
    ``True`` when :func:`extract_orcid` can extract an ORCID iD; otherwise
    ``False``.
"""
    return extract_orcid(value) is not None

def orcid_url(orcid: str | None) -> str | None:
    """Return the canonical ORCID URL for an ORCID-like value.

Args:
    orcid: A bare ORCID iD, ORCID URL, or other ORCID-like text.

Returns:
    A canonical URL such as ``"https://orcid.org/0000-0002-0254-6627"``, or
    ``None`` if the input does not contain an ORCID iD.
"""
    bare = extract_orcid(orcid)
    if not bare:
        return None
    return f"https://orcid.org/{bare}"

def _quote_doi_for_path(doi: str) -> str:
    """
    Quote a DOI for APIs that place the DOI inside a URL path segment.

    The slash between the DOI prefix and suffix must be encoded for APIs like
    Crossref and DataCite path lookups.
    """
    return quote(doi, safe="")

def _quote_doi_for_doi_org(doi: str) -> str:
    """
    Quote a DOI for doi.org URLs.

    doi.org handles ordinary DOI slashes naturally, so leave slashes unescaped
    while escaping spaces and other awkward characters.
    """
    return quote(doi, safe="/:")

def _normalize_for_match(text: str | None) -> str:
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

def _contains_normalized(haystack: str | None, needle: str | None) -> bool:
    """Case/punctuation/whitespace-insensitive substring check."""
    normalized_haystack = _normalize_for_match(haystack)
    normalized_needle = _normalize_for_match(needle)
    if not normalized_needle:
        return True
    return normalized_needle in normalized_haystack

def _title_similarity(a: str | None, b: str | None) -> float:
    """Return a simple normalized-title similarity ratio."""
    na = _normalize_for_match(a)
    nb = _normalize_for_match(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()

def _split_words(text: str | None) -> set[str]:
    """Return normalized word tokens, ignoring tiny stop words."""
    stop = {"a", "an", "and", "by", "for", "in", "of", "on", "the", "to", "with"}
    return {
        word
        for word in _normalize_for_match(text).split()
        if len(word) > 2 and word not in stop
    }

def _author_lastish_name(name: str) -> str:
    """Return a useful normalized author token for overlap checks."""
    raw = html.unescape(str(name or "")).strip()

    # Many metadata services use "Family, Given" while others use
    # "Given Family". Treat the part before a comma as the family-name-ish
    # token so "Starnini, Michele" overlaps with "Michele Starnini".
    if "," in raw:
        normalized_comma_family = _normalize_for_match(raw.split(",", 1)[0])
        if normalized_comma_family:
            return normalized_comma_family.split()[-1]

    normalized = _normalize_for_match(raw)
    if not normalized:
        return ""
    parts = normalized.split()
    return parts[-1]

def _author_overlap(a: list[str], b: list[str]) -> bool:
    """Return True if two author lists share an apparent surname/name token."""
    a_names = {_author_lastish_name(name) for name in a if _author_lastish_name(name)}
    b_names = {_author_lastish_name(name) for name in b if _author_lastish_name(name)}
    return bool(a_names and b_names and a_names.intersection(b_names))

def _get_year_from_crossref(data: dict[str, Any]) -> int | None:
    """Extract the best available publication year from Crossref metadata."""
    for field in ("published-print", "published-online", "published", "issued"):
        date_parts = data.get(field, {}).get("date-parts")
        if date_parts and date_parts[0]:
            return date_parts[0][0]
    return None

def _get_year_from_date(value: str | None) -> int | None:
    """Extract a four-digit year from an ISO-ish date string."""
    if not value:
        return None
    match = re.search(r"\b(\d{4})\b", value)
    if not match:
        return None
    return int(match.group(1))

def extract_arxiv_id(value: str | None) -> str | None:
    """Extract a modern or old-style arXiv ID from text or URL.

Args:
    value: Text that may contain a bare arXiv ID, ``arXiv:``-prefixed ID, or an
        arXiv abstract/PDF URL.

Returns:
    The arXiv ID as written, including a version suffix when present, or
    ``None`` when no arXiv identifier is present.
"""
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
    """Strip an arXiv version suffix for deduplication.

Args:
    arxiv_id: An arXiv identifier such as ``"2501.01234v2"``.

Returns:
    The identifier without its trailing version suffix, such as
    ``"2501.01234"``, or ``None`` for empty input.
"""
    if not arxiv_id:
        return None
    return re.sub(r"v\d+$", "", arxiv_id.strip(), flags=re.IGNORECASE)

def _find_arxiv_id_in_mapping(mapping: dict[str, Any]) -> str | None:
    """Recursively look for an arXiv ID in a nested dict/list structure."""
    for value in mapping.values():
        if isinstance(value, str):
            found = extract_arxiv_id(value)
            if found:
                return found
        elif isinstance(value, dict):
            found = _find_arxiv_id_in_mapping(value)
            if found:
                return found
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    found = extract_arxiv_id(item)
                    if found:
                        return found
                elif isinstance(item, dict):
                    found = _find_arxiv_id_in_mapping(item)
                    if found:
                        return found
    return None

def make_arxiv_url(arxiv_id: str | None) -> str:
    """Return the canonical arXiv abstract URL for an ID.

Args:
    arxiv_id: A bare arXiv identifier, optionally with an ``arXiv:`` prefix,
        URL wrapper, or version suffix.

Returns:
    The canonical abstract URL. Empty or unparseable input produces the empty
    string.
"""
    return f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""

def _maybe_int(value: Any) -> int | None:
    """Best-effort integer conversion."""
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
