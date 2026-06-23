#!/usr/bin/env python3
"""
doi.py

A small CLI helper for finding scholarly works and fetching metadata.

This began life as a DOI lookup helper. It is now deliberately broader:
search/discovery returns work candidates even when no DOI is available. DOI is
an important identifier, but not the gatekeeper.

Search/discovery paths:

  - OpenAlex work search, including DOI-less records
  - Crossref bibliographic search
  - DataCite DOI metadata search
  - arXiv Atom API search

When a selected work has a DOI, the script can still enrich it through:

  - Crossref for structured metadata
  - DataCite as a structured metadata fallback
  - OpenAlex for author ORCIDs
  - doi.org content negotiation for BibTeX

When a selected work does not have a DOI, the script prints the best metadata it
has and can generate a BibTeX-like entry from the available identifiers, such as
arXiv and OpenAlex IDs.
"""

from __future__ import annotations

import html
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pprint import pformat
from typing import Any
from urllib.parse import quote

import pydoc
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------
# Request helpers
# ---------------------------------------------------------

DEFAULT_TIMEOUT = 20
MAX_CANDIDATES_PER_SOURCE = 50
MAX_DISPLAY_CANDIDATES = 30

# Crossref recommends identifying scripts that use its API. Keeping the email
# configurable makes the script easier to share later.
#
# DOI_EMAIL is the preferred setting name for this script. DOI_PLAY_EMAIL is
# accepted as an older/backward-compatible name.
CONTACT_EMAIL = os.getenv("DOI_EMAIL") or os.getenv("DOI_PLAY_EMAIL", "")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")

if CONTACT_EMAIL:
    USER_AGENT = f"doi/0.2 (mailto:{CONTACT_EMAIL})"
else:
    USER_AGENT = "doi/0.2"

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
}


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


# ---------------------------------------------------------
# Small normalization helpers
# ---------------------------------------------------------


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


def author_names_from_crossref(item: dict[str, Any]) -> list[str]:
    """Return author display names from a Crossref item."""
    names = []
    for author in item.get("author", []):
        name = f"{author.get('given', '')} {author.get('family', '')}".strip()
        if name:
            names.append(name)
    return names


def author_names_from_openalex(item: dict[str, Any]) -> list[str]:
    """Return author display names from an OpenAlex item."""
    names = []
    for authorship in item.get("authorships", []):
        name = authorship.get("author", {}).get("display_name", "")
        if name:
            names.append(name)
    return names


def author_names_from_datacite(attributes: dict[str, Any]) -> list[str]:
    """Return creator display names from a DataCite metadata record."""
    names = []
    for creator in attributes.get("creators", []):
        name = creator.get("name")
        if not name:
            name = f"{creator.get('givenName', '')} {creator.get('familyName', '')}"
        name = name.strip()
        if name:
            names.append(name)
    return names


def get_title_from_datacite(attributes: dict[str, Any]) -> str:
    """Return the first title from a DataCite metadata record."""
    for title in attributes.get("titles", []):
        title_text = title.get("title", "").strip()
        if title_text:
            return html.unescape(title_text)
    return ""


def get_type_from_datacite(attributes: dict[str, Any]) -> str:
    """Return the most useful type string from a DataCite metadata record."""
    types = attributes.get("types") or {}
    return types.get("resourceType") or types.get("resourceTypeGeneral") or ""


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


# ---------------------------------------------------------
# DOI metadata and lookup functions
# ---------------------------------------------------------


def get_metadata_from_crossref(doi: str) -> dict[str, Any] | None:
    """
    Fetch structured metadata for a DOI from Crossref.

    Important: this is a Crossref-specific lookup. It can fail for perfectly
    valid DOIs that are registered with another DOI registration agency.
    """
    doi = clean_doi(doi)
    if not doi:
        return None

    url = f"https://api.crossref.org/works/{quote_doi_for_path(doi)}"
    data = fetch_json(url, source="Crossref", params=crossref_params())
    if not data:
        return None

    message = data.get("message")
    if not isinstance(message, dict):
        print("Crossref response did not contain the expected metadata block.")
        return None

    return {
        "source": "Crossref",
        "doi": message.get("DOI", doi),
        "title": first(message.get("title"), ""),
        "authors": author_names_from_crossref(message),
        "journal": first(message.get("container-title"), ""),
        "publisher": message.get("publisher", ""),
        "citations": message.get("is-referenced-by-count", 0),
        "year": get_year_from_crossref(message),
        "type": message.get("type", ""),
        "url": message.get("URL", ""),
    }


def get_metadata_from_datacite(doi: str) -> dict[str, Any] | None:
    """
    Fetch structured metadata for a DOI from DataCite.

    DataCite is a separate DOI registration agency from Crossref. This lookup is
    useful when a DOI is valid but Crossref does not have a metadata record for
    it, which is common for datasets, software, preprints, and repository items.
    """
    doi = clean_doi(doi)
    if not doi:
        return None

    url = f"https://api.datacite.org/dois/{quote_doi_for_path(doi)}"
    data = fetch_json(url, source="DataCite")
    if not data:
        return None

    record = data.get("data")
    if not isinstance(record, dict):
        print("DataCite response did not contain the expected data block.")
        return None

    attributes = record.get("attributes")
    if not isinstance(attributes, dict):
        print("DataCite response did not contain the expected metadata attributes.")
        return None

    return {
        "source": "DataCite",
        "doi": attributes.get("doi") or record.get("id") or doi,
        "title": get_title_from_datacite(attributes),
        "authors": author_names_from_datacite(attributes),
        "journal": "",
        "publisher": attributes.get("publisher", ""),
        "citations": attributes.get("citationCount", 0),
        "year": attributes.get("publicationYear"),
        "type": get_type_from_datacite(attributes),
        "url": attributes.get("url", ""),
    }


def get_best_structured_metadata(doi: str) -> dict[str, Any] | None:
    """
    Fetch structured DOI metadata, trying Crossref first and DataCite second.

    Crossref remains the preferred metadata source for journal/conference-style
    publications. DataCite is tried only when Crossref has no usable record.
    """
    metadata = get_metadata_from_crossref(doi)
    if metadata is not None:
        return metadata

    print("No Crossref metadata found. Checking DataCite as a fallback...")
    return get_metadata_from_datacite(doi)


def get_bibtex_from_doi(doi: str) -> str | None:
    """
    Retrieve BibTeX formatting from doi.org via content negotiation.

    This can work beyond Crossref DOIs, because the request goes through the DOI
    resolver rather than directly to Crossref.
    """
    doi = clean_doi(doi)
    if not doi:
        return None

    url = f"https://doi.org/{quote_doi_for_doi_org(doi)}"
    headers = {"Accept": "application/x-bibtex"}
    return fetch_text(url, source="doi.org BibTeX", headers=headers)


def get_orcids_from_openalex(doi: str) -> list[dict[str, str]]:
    """Extract author ORCIDs using OpenAlex."""
    doi = clean_doi(doi)
    if not doi:
        return []

    # OpenAlex accepts external IDs in the form doi:<bare-doi>.
    openalex_work_id = quote(f"doi:{doi}", safe=":")
    url = f"https://api.openalex.org/works/{openalex_work_id}"
    data = fetch_json(url, source="OpenAlex", params=openalex_params())
    if not data:
        return []

    orcids = []
    for authorship in data.get("authorships", []):
        author = authorship.get("author", {})
        orcid_url = author.get("orcid")

        # If OpenAlex has an ORCID for this author, it will usually be a full URL.
        if orcid_url:
            name = author.get("display_name", "").strip()
            orcid_id = orcid_url.split("/")[-1]
            orcids.append({"name": name, "orcid": orcid_id})

    return orcids


def get_orcids_from_crossref(doi: str) -> list[dict[str, str]]:
    """
    Extract author ORCIDs from Crossref metadata, if provided by the publisher.

    This function is currently unused by the CLI, but is kept as a useful
    comparison with OpenAlex ORCID coverage.
    """
    doi = clean_doi(doi)
    if not doi:
        return []

    url = f"https://api.crossref.org/works/{quote_doi_for_path(doi)}"
    data = fetch_json(url, source="Crossref", params=crossref_params())
    if not data:
        return []

    authors = data.get("message", {}).get("author", [])
    orcids = []
    for author in authors:
        # If the publisher provided an ORCID, it will be here.
        if "ORCID" in author:
            name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            orcid_id = author["ORCID"].split("/")[-1]
            orcids.append({"name": name, "orcid": orcid_id})

    return orcids


# ---------------------------------------------------------
# Candidate conversion functions
# ---------------------------------------------------------


def canonical_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Ensure optional candidate fields exist and normalize identifiers."""
    candidate = dict(candidate)
    candidate["doi"] = clean_doi(candidate.get("doi"))
    candidate["arxiv_id"] = base_arxiv_id(candidate.get("arxiv_id") or extract_arxiv_id(candidate.get("url")))
    candidate.setdefault("openalex_id", "")
    candidate.setdefault("url", "")
    candidate.setdefault("authors", [])
    candidate.setdefault("title", "")
    candidate.setdefault("venue", "")
    candidate.setdefault("publisher", "")
    candidate.setdefault("type", "")
    candidate.setdefault("cited_by_count", 0)
    candidate.setdefault("metadata_sources", [])

    source = candidate.get("source")
    if source and source not in candidate["metadata_sources"]:
        candidate["metadata_sources"].append(source)

    if candidate["arxiv_id"] and not candidate.get("url"):
        candidate["url"] = make_arxiv_url(candidate["arxiv_id"])

    if candidate.get("doi") and not candidate.get("url"):
        candidate["url"] = f"https://doi.org/{quote_doi_for_doi_org(candidate['doi'])}"

    return candidate


def crossref_item_to_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a Crossref result item into a work candidate dictionary."""
    title = first(item.get("title"), "")
    doi = clean_doi(item.get("DOI"))
    if not title and not doi:
        return None

    candidate = {
        "doi": doi,
        "arxiv_id": extract_arxiv_id(item.get("URL", "")),
        "openalex_id": "",
        "title": title,
        "year": get_year_from_crossref(item),
        "authors": author_names_from_crossref(item),
        "venue": first(item.get("container-title"), ""),
        "publisher": item.get("publisher", ""),
        "cited_by_count": item.get("is-referenced-by-count", 0),
        "type": item.get("type", ""),
        "source": "Crossref",
        "id": item.get("URL", ""),
        "url": item.get("URL", ""),
    }
    return canonical_candidate(candidate)


def best_openalex_url(item: dict[str, Any]) -> str:
    """Return the best human landing URL in an OpenAlex work record."""
    primary_location = item.get("primary_location") or {}
    landing = primary_location.get("landing_page_url") or ""
    if landing:
        return landing

    for location in item.get("locations") or []:
        landing = location.get("landing_page_url") or ""
        if landing:
            return landing

    ids = item.get("ids") or {}
    for key in ("doi", "pmcid", "pmid"):
        if ids.get(key):
            return ids[key]

    return item.get("id", "") or ""


def openalex_item_to_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert an OpenAlex work item into a work candidate dictionary."""
    ids = item.get("ids") or {}
    doi = clean_doi(item.get("doi") or ids.get("doi"))

    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    url = best_openalex_url(item)
    arxiv_id = find_arxiv_id_in_mapping(item)

    title = item.get("title", "") or item.get("display_name", "") or ""
    if not title and not doi and not arxiv_id:
        return None

    candidate = {
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": item.get("id", ""),
        "title": title,
        "year": item.get("publication_year"),
        "authors": author_names_from_openalex(item),
        "venue": source.get("display_name", "") or "",
        "publisher": source.get("host_organization_name", "") or "",
        "cited_by_count": item.get("cited_by_count", 0),
        "type": item.get("type", ""),
        "source": "OpenAlex",
        "id": item.get("id", ""),
        "url": url,
    }
    return canonical_candidate(candidate)


def datacite_record_to_candidate(record: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a DataCite DOI record into a work candidate dictionary."""
    attributes = record.get("attributes") or {}
    doi = clean_doi(attributes.get("doi") or record.get("id"))
    title = get_title_from_datacite(attributes)
    if not title and not doi:
        return None

    url = attributes.get("url") or ""
    candidate = {
        "doi": doi,
        "arxiv_id": extract_arxiv_id(url) or find_arxiv_id_in_mapping(attributes),
        "openalex_id": "",
        "title": title,
        "year": attributes.get("publicationYear"),
        "authors": author_names_from_datacite(attributes),
        "venue": attributes.get("container", {}).get("title", "") if isinstance(attributes.get("container"), dict) else "",
        "publisher": attributes.get("publisher", ""),
        "cited_by_count": attributes.get("citationCount", 0),
        "type": get_type_from_datacite(attributes),
        "source": "DataCite",
        "id": record.get("id", ""),
        "url": url,
    }
    return canonical_candidate(candidate)


def arxiv_entry_to_candidate(entry: ET.Element) -> dict[str, Any] | None:
    """Convert an arXiv Atom feed entry into a work candidate dictionary."""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    def text(path: str) -> str:
        element = entry.find(path, ns)
        return element.text.strip() if element is not None and element.text else ""

    title = re.sub(r"\s+", " ", text("atom:title")).strip()
    arxiv_url = text("atom:id")
    arxiv_id = extract_arxiv_id(arxiv_url)
    year = get_year_from_date(text("atom:published"))

    authors = []
    for author in entry.findall("atom:author", ns):
        name = author.find("atom:name", ns)
        if name is not None and name.text:
            authors.append(name.text.strip())

    doi = clean_doi(text("arxiv:doi"))
    journal_ref = text("arxiv:journal_ref")
    primary_category = entry.find("arxiv:primary_category", ns)
    category = primary_category.attrib.get("term", "") if primary_category is not None else ""

    if not title and not arxiv_id and not doi:
        return None

    candidate = {
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": "",
        "title": html.unescape(title),
        "year": year,
        "authors": authors,
        "venue": journal_ref or "arXiv",
        "publisher": "arXiv",
        "cited_by_count": 0,
        "type": "preprint",
        "source": "arXiv",
        "id": arxiv_url,
        "url": arxiv_url or make_arxiv_url(arxiv_id),
        "arxiv_category": category,
    }
    return canonical_candidate(candidate)


# ---------------------------------------------------------
# Candidate matching, scoring, and merging
# ---------------------------------------------------------


def candidate_matches(
    candidate: dict[str, Any],
    *,
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
    allow_loose_title: bool = False,
) -> bool:
    """Apply local matching to a structured work candidate."""
    if title:
        if allow_loose_title:
            query_words = split_words(title)
            candidate_words = split_words(candidate.get("title"))
            if query_words and not query_words.intersection(candidate_words):
                return False
        elif not contains_normalized(candidate.get("title"), title):
            return False

    if author:
        authors = candidate.get("authors", [])
        if not any(contains_normalized(name, author) for name in authors):
            return False

    if year:
        if str(candidate.get("year")) != str(year).strip():
            return False

    return True




def candidate_search_text(candidate: dict[str, Any]) -> str:
    """Return a broad text blob for loose all-fields matching."""
    parts: list[str] = []
    for key in ("title", "venue", "publisher", "type", "doi", "arxiv_id", "openalex_id", "url"):
        value = candidate.get(key)
        if value:
            parts.append(str(value))
    parts.extend(str(name) for name in candidate.get("authors", []) if name)
    return " ".join(parts)


def candidate_matches_loose_query(
    candidate: dict[str, Any],
    query: str | None,
    *,
    year: str | int | None = None,
) -> bool:
    """
    Apply a broad all-fields match.

    This fallback is intentionally different from title/author matching: it is
    meant to recover from underspecified searches and accidental title/author
    swaps such as title="starnini", author="opinion dynamics".
    """
    if year and str(candidate.get("year")) != str(year).strip():
        return False

    query_words = split_words(query)
    if not query_words:
        return True

    candidate_words = split_words(candidate_search_text(candidate))
    if not candidate_words:
        return False

    shared = query_words.intersection(candidate_words)

    # For short queries, require every significant token. For longer queries,
    # require most of them so a missing subtitle word does not kill the match.
    if len(query_words) <= 4:
        return query_words.issubset(candidate_words)

    return len(shared) >= max(4, int(len(query_words) * 0.75))


def candidate_score(
    candidate: dict[str, Any],
    *,
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> tuple[int, int]:
    """
    Return a simple ranking score for a work candidate.

    The score is a local approximation of relevance. Matching decides whether to
    include a candidate; scoring decides which plausible candidates come first.
    """
    score = 0

    candidate_title = normalize_for_match(candidate.get("title"))
    query_title = normalize_for_match(title)

    if query_title:
        similarity = title_similarity(candidate_title, query_title)
        if candidate_title == query_title:
            score += 100
        elif candidate_title.startswith(query_title):
            score += 85
        elif query_title in candidate_title:
            score += 70
        elif similarity >= 0.90:
            score += 65
        elif similarity >= 0.75:
            score += 45
        else:
            shared = split_words(candidate_title).intersection(split_words(query_title))
            score += min(35, len(shared) * 8)

        # Prefer tight title matches over much longer titles that merely
        # contain the query as a substring.
        title_word_gap = abs(
            len(candidate_title.split()) - len(query_title.split())
        )
        score -= min(title_word_gap, 25)

    if author:
        query_author = normalize_for_match(author)
        candidate_authors = [
            normalize_for_match(name)
            for name in candidate.get("authors", [])
        ]

        if any(name == query_author for name in candidate_authors):
            score += 50
        elif any(query_author in name for name in candidate_authors):
            score += 40

        # If the user supplied one author, a first-author match is a useful
        # signal, especially for quick scholarly metadata lookup.
        if candidate_authors and query_author in candidate_authors[0]:
            score += 10

    if year and str(candidate.get("year")) == str(year).strip():
        score += 30

    # Identifier bonuses are deliberately small. A DOI is useful, but DOI-less
    # works should still be visible and selectable.
    if candidate.get("doi"):
        score += 10
    if candidate.get("arxiv_id"):
        score += 8
    if candidate.get("openalex_id"):
        score += 5

    # Prefer records seen by multiple services.
    score += min(12, max(0, len(candidate.get("metadata_sources", [])) - 1) * 4)

    # Very weak tie-breaker. Citation count should not overpower title, author,
    # or year matching.
    try:
        citations = int(candidate.get("cited_by_count") or 0)
    except (TypeError, ValueError):
        citations = 0
    citation_bonus = min(citations, 1000)

    return score, citation_bonus


def add_candidate_score(
    candidate: dict[str, Any],
    *,
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> dict[str, Any]:
    """Attach the local ranking score to a candidate for display/debugging."""
    score, citation_bonus = candidate_score(
        candidate,
        author=author,
        title=title,
        year=year,
    )
    candidate["score"] = score
    candidate["citation_score"] = citation_bonus
    return candidate




def add_best_candidate_score(
    candidate: dict[str, Any],
    search_variants: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score a candidate using the best available interpretation of the query."""
    best_score: tuple[int, int] | None = None
    best_variant: dict[str, Any] | None = None

    for variant in search_variants:
        # Search variants may include private display annotations such as
        # _match_note. Only pass the fields candidate_score() understands.
        score_kwargs = {
            key: value
            for key, value in variant.items()
            if key in {"author", "title", "year"}
        }
        score = candidate_score(candidate, **score_kwargs)
        if best_score is None or score > best_score:
            best_score = score
            best_variant = variant

    if best_score is None:
        best_score = (0, 0)
        best_variant = {}

    candidate["score"] = best_score[0]
    candidate["citation_score"] = best_score[1]

    # Prefer a note attached by the search path that actually produced the
    # candidate. Fall back to the best-scoring query interpretation only when
    # the source path did not annotate the record.
    if candidate.get("_match_note"):
        candidate["match_note"] = candidate["_match_note"]
    elif best_variant and best_variant.get("_match_note"):
        candidate["match_note"] = best_variant["_match_note"]

    return candidate


def candidates_are_same(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Return True if two candidates appear to describe the same work."""
    doi_a = clean_doi(a.get("doi"))
    doi_b = clean_doi(b.get("doi"))
    if doi_a and doi_b and doi_a.casefold() == doi_b.casefold():
        return True

    arxiv_a = base_arxiv_id(a.get("arxiv_id"))
    arxiv_b = base_arxiv_id(b.get("arxiv_id"))
    if arxiv_a and arxiv_b and arxiv_a.casefold() == arxiv_b.casefold():
        return True

    openalex_a = a.get("openalex_id")
    openalex_b = b.get("openalex_id")
    if openalex_a and openalex_b and openalex_a == openalex_b:
        return True

    if a.get("year") and b.get("year") and str(a.get("year")) != str(b.get("year")):
        return False

    similar_title = title_similarity(a.get("title"), b.get("title")) >= 0.92
    if not similar_title:
        return False

    # If author lists are present, require some overlap. If one source omitted
    # authors, high title/year similarity is enough.
    authors_a = a.get("authors", [])
    authors_b = b.get("authors", [])
    if authors_a and authors_b:
        return author_overlap(authors_a, authors_b)

    return True


def merge_candidates(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Merge two candidates that appear to be the same work."""
    merged = dict(primary)

    # Prefer existing values, but fill blanks from the secondary record.
    for key in (
        "doi",
        "arxiv_id",
        "openalex_id",
        "title",
        "year",
        "venue",
        "publisher",
        "type",
        "url",
        "id",
    ):
        if not merged.get(key) and secondary.get(key):
            merged[key] = secondary[key]

    # Prefer a longer, more complete title if the current one is suspiciously short.
    if len(str(secondary.get("title") or "")) > len(str(merged.get("title") or "")) + 10:
        if title_similarity(merged.get("title"), secondary.get("title")) >= 0.85:
            merged["title"] = secondary["title"]

    if not merged.get("authors") and secondary.get("authors"):
        merged["authors"] = secondary["authors"]
    elif merged.get("authors") and secondary.get("authors"):
        names = list(merged["authors"])
        seen = {normalize_for_match(name) for name in names}
        for name in secondary["authors"]:
            if normalize_for_match(name) not in seen:
                names.append(name)
                seen.add(normalize_for_match(name))
        merged["authors"] = names

    merged["cited_by_count"] = max(
        maybe_int(merged.get("cited_by_count")) or 0,
        maybe_int(secondary.get("cited_by_count")) or 0,
    )

    sources = []
    for source in merged.get("metadata_sources", []) + secondary.get("metadata_sources", []):
        if source and source not in sources:
            sources.append(source)
    if secondary.get("source") and secondary.get("source") not in sources:
        sources.append(secondary["source"])
    merged["metadata_sources"] = sources

    if secondary.get("arxiv_category") and not merged.get("arxiv_category"):
        merged["arxiv_category"] = secondary["arxiv_category"]

    return canonical_candidate(merged)


def merge_candidate_list(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge candidates from multiple metadata sources."""
    merged: list[dict[str, Any]] = []

    for candidate in candidates:
        candidate = canonical_candidate(candidate)
        match_index = None
        for i, existing in enumerate(merged):
            if candidates_are_same(existing, candidate):
                match_index = i
                break

        if match_index is None:
            merged.append(candidate)
        else:
            merged[match_index] = merge_candidates(merged[match_index], candidate)

    return merged


# ---------------------------------------------------------
# Search functions
# ---------------------------------------------------------


def bibliographic_query(author: str | None, title: str | None, year: str | int | None) -> str:
    """Build a compact bibliographic query string from available fields."""
    parts = []
    if title:
        parts.append(str(title).strip())
    if author:
        parts.append(str(author).strip())
    if year:
        parts.append(str(year).strip())
    return " ".join(part for part in parts if part)


def get_work_candidates_from_crossref(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch work candidates from Crossref bibliographic search."""
    url = "https://api.crossref.org/works"

    params: dict[str, Any] = {
        "rows": MAX_CANDIDATES_PER_SOURCE,
        "query.bibliographic": bibliographic_query(author, title, year),
    }
    if author:
        params["query.author"] = author
    if title:
        params["query.title"] = title
    if year:
        params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"

    data = fetch_json(url, source="Crossref", params=crossref_params(params))
    if not data:
        return []

    items = data.get("message", {}).get("items", [])
    matched = []

    for item in items:
        candidate = crossref_item_to_candidate(item)
        if not candidate:
            continue
        if candidate_matches(candidate, author=author, title=title, year=year, allow_loose_title=True):
            add_candidate_score(candidate, author=author, title=title, year=year)
            matched.append(candidate)

    return matched


def get_work_candidates_from_openalex(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch work candidates from OpenAlex matching the provided criteria.

    Unlike the earlier DOI-only version, this function deliberately keeps
    DOI-less OpenAlex works.
    """
    url = "https://api.openalex.org/works"

    params: dict[str, Any] = {
        "per-page": MAX_CANDIDATES_PER_SOURCE,
    }

    # Prefer title for discovery; fall back to author. If both are present,
    # searching the title usually keeps the result set narrow and accurate.
    if title:
        params["search"] = title
    elif author:
        params["search"] = author

    filters = []
    if year:
        year_text = str(year).strip()
        if re.fullmatch(r"\d{4}", year_text):
            filters.append(f"publication_year:{year_text}")

    if filters:
        params["filter"] = ",".join(filters)

    data = fetch_json(url, source="OpenAlex", params=openalex_params(params))
    if not data:
        return []

    items = data.get("results", [])
    matched = []

    for item in items:
        candidate = openalex_item_to_candidate(item)
        if not candidate:
            continue
        if not candidate_matches(candidate, author=author, title=title, year=year, allow_loose_title=False):
            continue
        add_candidate_score(candidate, author=author, title=title, year=year)
        matched.append(candidate)

    return matched


def get_work_candidates_from_datacite(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch work candidates from DataCite DOI metadata search."""
    url = "https://api.datacite.org/dois"
    query = bibliographic_query(author, title, year)
    if not query:
        return []

    params: dict[str, Any] = {
        "page[size]": MAX_CANDIDATES_PER_SOURCE,
        "query": query,
    }
    if year:
        params["publicationYear"] = str(year).strip()

    data = fetch_json(url, source="DataCite", params=params)
    if not data:
        return []

    records = data.get("data", [])
    matched = []

    for record in records:
        candidate = datacite_record_to_candidate(record)
        if not candidate:
            continue
        if candidate_matches(candidate, author=author, title=title, year=year, allow_loose_title=True):
            add_candidate_score(candidate, author=author, title=title, year=year)
            matched.append(candidate)

    return matched


def arxiv_search_query(author: str | None, title: str | None, year: str | int | None) -> str:
    """Build an arXiv API search_query string."""
    terms = []
    if title:
        # ti: searches title. Parentheses help with multi-word title fragments.
        terms.append(f'ti:"{title}"')
    if author:
        terms.append(f'au:"{author}"')
    if not terms:
        terms.append("all:*")
    # arXiv API has date filters, but local year filtering is simpler and more
    # robust for this small interactive script.
    return " AND ".join(terms)


def get_work_candidates_from_arxiv(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch work candidates from the arXiv Atom API."""
    if not title and not author:
        return []

    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": arxiv_search_query(author, title, year),
        "start": 0,
        "max_results": min(MAX_CANDIDATES_PER_SOURCE, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    text = fetch_text(url, source="arXiv", params=params)
    if not text:
        return []

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        print("arXiv returned a response, but it was not valid Atom XML.")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    matched = []
    for entry in root.findall("atom:entry", ns):
        candidate = arxiv_entry_to_candidate(entry)
        if not candidate:
            continue
        if candidate_matches(candidate, author=author, title=title, year=year, allow_loose_title=True):
            add_candidate_score(candidate, author=author, title=title, year=year)
            matched.append(candidate)

    return matched


def get_candidate_from_openalex_id(openalex_id: str) -> dict[str, Any] | None:
    """Fetch a single candidate by OpenAlex work ID or URL."""
    value = openalex_id.strip()
    if not value:
        return None

    if value.startswith("https://openalex.org/"):
        work_id = value.rsplit("/", 1)[-1]
    else:
        work_id = value

    url = f"https://api.openalex.org/works/{quote(work_id, safe='')}"
    data = fetch_json(url, source="OpenAlex", params=openalex_params())
    if not data:
        return None

    return openalex_item_to_candidate(data)


def get_candidate_from_arxiv_id(arxiv_id: str) -> dict[str, Any] | None:
    """Fetch a single candidate by arXiv ID."""
    arxiv_id = base_arxiv_id(extract_arxiv_id(arxiv_id) or arxiv_id)
    if not arxiv_id:
        return None

    url = "https://export.arxiv.org/api/query"
    params = {"id_list": arxiv_id, "max_results": 1}
    text = fetch_text(url, source="arXiv", params=params)
    if not text:
        return None

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        print("arXiv returned a response, but it was not valid Atom XML.")
        return None

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return None

    return arxiv_entry_to_candidate(entry)


def get_candidate_from_doi(doi: str) -> dict[str, Any] | None:
    """Build a single candidate around a known DOI, enriched where possible."""
    doi = clean_doi(doi)
    if not doi:
        return None

    candidates: list[dict[str, Any]] = []

    metadata = get_metadata_from_crossref(doi)
    if metadata:
        candidate = {
            "doi": doi,
            "title": metadata.get("title", ""),
            "year": metadata.get("year"),
            "authors": metadata.get("authors", []),
            "venue": metadata.get("journal", ""),
            "publisher": metadata.get("publisher", ""),
            "cited_by_count": metadata.get("citations", 0),
            "type": metadata.get("type", ""),
            "source": "Crossref",
            "url": metadata.get("url", ""),
        }
        candidates.append(canonical_candidate(candidate))

    datacite = get_metadata_from_datacite(doi)
    if datacite:
        candidate = {
            "doi": doi,
            "title": datacite.get("title", ""),
            "year": datacite.get("year"),
            "authors": datacite.get("authors", []),
            "venue": datacite.get("journal", ""),
            "publisher": datacite.get("publisher", ""),
            "cited_by_count": datacite.get("citations", 0),
            "type": datacite.get("type", ""),
            "source": "DataCite",
            "url": datacite.get("url", ""),
        }
        candidates.append(canonical_candidate(candidate))

    # OpenAlex may have ORCIDs, citation counts, and a better landing page.
    openalex_work_id = quote(f"doi:{doi}", safe=":")
    openalex_url = f"https://api.openalex.org/works/{openalex_work_id}"
    openalex_data = fetch_json(openalex_url, source="OpenAlex", params=openalex_params())
    if openalex_data:
        openalex_candidate = openalex_item_to_candidate(openalex_data)
        if openalex_candidate:
            candidates.append(openalex_candidate)

    if not candidates:
        return canonical_candidate({
            "doi": doi,
            "title": "",
            "year": None,
            "authors": [],
            "venue": "",
            "publisher": "",
            "cited_by_count": 0,
            "type": "",
            "source": "user-supplied DOI",
            "url": f"https://doi.org/{quote_doi_for_doi_org(doi)}",
        })

    merged = merge_candidate_list(candidates)
    return merged[0] if merged else None




def get_work_candidates_from_openalex_loose(
    query: str,
    *,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch OpenAlex candidates using a broad all-fields fallback query."""
    if not query.strip():
        return []

    url = "https://api.openalex.org/works"
    params: dict[str, Any] = {
        "per-page": MAX_CANDIDATES_PER_SOURCE,
        "search": query,
    }

    filters = []
    if year:
        year_text = str(year).strip()
        if re.fullmatch(r"\d{4}", year_text):
            filters.append(f"publication_year:{year_text}")
    if filters:
        params["filter"] = ",".join(filters)

    data = fetch_json(url, source="OpenAlex", params=openalex_params(params))
    if not data:
        return []

    matched = []
    for item in data.get("results", []):
        candidate = openalex_item_to_candidate(item)
        if not candidate:
            continue
        if not candidate_matches_loose_query(candidate, query, year=year):
            continue
        matched.append(candidate)

    return matched


def get_work_candidates_from_crossref_loose(
    query: str,
    *,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch Crossref candidates using only broad bibliographic search."""
    if not query.strip():
        return []

    url = "https://api.crossref.org/works"
    params: dict[str, Any] = {
        "rows": MAX_CANDIDATES_PER_SOURCE,
        "query.bibliographic": query,
    }
    if year:
        params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"

    data = fetch_json(url, source="Crossref", params=crossref_params(params))
    if not data:
        return []

    matched = []
    for item in data.get("message", {}).get("items", []):
        candidate = crossref_item_to_candidate(item)
        if not candidate:
            continue
        if not candidate_matches_loose_query(candidate, query, year=year):
            continue
        matched.append(candidate)

    return matched


def get_work_candidates_from_datacite_loose(
    query: str,
    *,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch DataCite candidates using broad metadata search."""
    if not query.strip():
        return []

    url = "https://api.datacite.org/dois"
    params: dict[str, Any] = {
        "page[size]": MAX_CANDIDATES_PER_SOURCE,
        "query": query,
    }
    if year:
        params["publicationYear"] = str(year).strip()

    data = fetch_json(url, source="DataCite", params=params)
    if not data:
        return []

    matched = []
    for record in data.get("data", []):
        candidate = datacite_record_to_candidate(record)
        if not candidate:
            continue
        if not candidate_matches_loose_query(candidate, query, year=year):
            continue
        matched.append(candidate)

    return matched


def arxiv_loose_search_query(query: str) -> str:
    """Build an arXiv all-fields query from significant normalized tokens."""
    terms = sorted(split_words(query))
    if not terms:
        return "all:*"
    return " AND ".join(f'all:"{term}"' for term in terms)


def get_work_candidates_from_arxiv_loose(
    query: str,
    *,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch arXiv candidates using a broad all-fields fallback query."""
    if not query.strip():
        return []

    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": arxiv_loose_search_query(query),
        "start": 0,
        "max_results": min(MAX_CANDIDATES_PER_SOURCE, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    text = fetch_text(url, source="arXiv", params=params)
    if not text:
        return []

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        print("arXiv returned a response, but it was not valid Atom XML.")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    matched = []
    for entry in root.findall("atom:entry", ns):
        candidate = arxiv_entry_to_candidate(entry)
        if not candidate:
            continue
        if not candidate_matches_loose_query(candidate, query, year=year):
            continue
        matched.append(candidate)

    return matched


def get_work_candidates_from_identifier(identifier: str) -> list[dict[str, Any]]:
    """Resolve a DOI, arXiv ID/URL, or OpenAlex work ID/URL to candidates."""
    identifier = identifier.strip()
    if not identifier:
        return []

    if looks_like_doi(identifier):
        candidate = get_candidate_from_doi(identifier)
        return [candidate] if candidate else []

    arxiv_id = extract_arxiv_id(identifier)
    if arxiv_id:
        candidate = get_candidate_from_arxiv_id(arxiv_id)
        return [candidate] if candidate else []

    if "openalex.org/" in identifier.lower() or re.fullmatch(r"W\d+", identifier.strip(), re.IGNORECASE):
        candidate = get_candidate_from_openalex_id(identifier)
        return [candidate] if candidate else []

    print("Identifier did not look like a DOI, arXiv ID/URL, or OpenAlex work ID/URL.")
    return []


def get_work_candidates(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
    identifier: str | None = None,
) -> list[dict[str, Any]]:
    """Search all configured metadata sources and return merged work candidates."""
    search_variants: list[dict[str, Any]] = [
        {"author": author, "title": title, "year": year},
    ]

    if identifier:
        candidates = get_work_candidates_from_identifier(identifier)
    else:
        candidates = []
        print("  OpenAlex...")
        candidates.extend(get_work_candidates_from_openalex(author=author, title=title, year=year))
        print("  Crossref...")
        candidates.extend(get_work_candidates_from_crossref(author=author, title=title, year=year))
        print("  DataCite...")
        candidates.extend(get_work_candidates_from_datacite(author=author, title=title, year=year))
        print("  arXiv...")
        candidates.extend(get_work_candidates_from_arxiv(author=author, title=title, year=year))

        # If title+author matching found nothing, try the most common data-entry
        # mistake: the user put the author in the title field and title words in
        # the author field. This is cheap and catches searches like
        # title="starnini", author="opinion dynamics".
        if not candidates and title and author:
            print("  No strict fielded matches. Trying title/author swapped...")
            swapped = {"author": title, "title": author, "year": year, "_match_note": "title/author swapped"}
            search_variants.append(swapped)
            swapped_candidates: list[dict[str, Any]] = []
            print("    OpenAlex...")
            swapped_candidates.extend(get_work_candidates_from_openalex(author=title, title=author, year=year))
            print("    Crossref...")
            swapped_candidates.extend(get_work_candidates_from_crossref(author=title, title=author, year=year))
            print("    DataCite...")
            swapped_candidates.extend(get_work_candidates_from_datacite(author=title, title=author, year=year))
            print("    arXiv...")
            swapped_candidates.extend(get_work_candidates_from_arxiv(author=title, title=author, year=year))
            for candidate in swapped_candidates:
                candidate["_match_note"] = "title/author swapped"
            candidates.extend(swapped_candidates)

        # Last resort: treat all supplied words as a broad bibliographic query,
        # then require those words to appear somewhere in title/authors/venue/IDs.
        # This protects the CLI from brittle API field semantics.
        if not candidates:
            loose_query = bibliographic_query(author, title, year=None)
            if loose_query:
                print("  No fielded matches. Trying broad all-fields fallback...")
                search_variants.append({"author": None, "title": loose_query, "year": year, "_match_note": "broad all-fields fallback"})
                loose_candidates: list[dict[str, Any]] = []
                print("    OpenAlex...")
                loose_candidates.extend(get_work_candidates_from_openalex_loose(loose_query, year=year))
                print("    Crossref...")
                loose_candidates.extend(get_work_candidates_from_crossref_loose(loose_query, year=year))
                print("    DataCite...")
                loose_candidates.extend(get_work_candidates_from_datacite_loose(loose_query, year=year))
                print("    arXiv...")
                loose_candidates.extend(get_work_candidates_from_arxiv_loose(loose_query, year=year))
                for candidate in loose_candidates:
                    candidate["_match_note"] = "broad all-fields fallback"
                candidates.extend(loose_candidates)

    merged = merge_candidate_list(candidates)
    for candidate in merged:
        add_best_candidate_score(candidate, search_variants)

    merged.sort(
        key=lambda c: (c.get("score") or 0, c.get("citation_score") or 0),
        reverse=True,
    )
    return merged

# Backward-compatible wrappers. The CLI now uses get_work_candidates(), but these
# names are kept in case you imported the old helpers elsewhere.

def get_doi_from_crossref(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Return Crossref candidates that have DOIs."""
    return [
        candidate
        for candidate in get_work_candidates_from_crossref(author=author, title=title, year=year)
        if candidate.get("doi")
    ]


def get_doi_from_openalex(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Return OpenAlex candidates that have DOIs."""
    return [
        candidate
        for candidate in get_work_candidates_from_openalex(author=author, title=title, year=year)
        if candidate.get("doi")
    ]


# ---------------------------------------------------------
# CLI formatting helpers
# ---------------------------------------------------------


def page_text(text: str) -> None:
    """Display long text through the user's pager."""
    pydoc.pager(text)


def print_search_data(search_data: dict[str, str | None]) -> None:
    """Cleanly format the current search criteria."""
    print("\nSearch data so far:")
    if not any(search_data.values()):
        print("(none)")
    else:
        if search_data.get("title"):
            print(f"title: {search_data['title']}")
        if search_data.get("author"):
            print(f"author: {search_data['author']}")
        if search_data.get("year"):
            print(f"year: {search_data['year']}")
        if search_data.get("identifier"):
            print(f"identifier: {search_data['identifier']}")


def format_authors(authors: list[str], max_authors: int = 4) -> str:
    """Return a compact author display string."""
    if not authors:
        return ""
    if len(authors) <= max_authors:
        return ", ".join(authors)
    return ", ".join(authors[:max_authors]) + ", et al."


def format_identifier_line(label: str, value: str | None) -> str:
    """Format one identifier line, showing an em dash for missing values."""
    return f"   {label}: {value or '—'}\n"


def serialize_candidate(
    candidate: dict[str, Any],
    index: int | None = None,
) -> str:
    """Return one structured work candidate."""
    prefix = f"{index}. " if index is not None else ""
    title = candidate.get("title") or "[No title]"
    year = candidate.get("year") or "n.d."
    authors = format_authors(candidate.get("authors", [])) or "[No authors listed]"
    venue = candidate.get("venue") or candidate.get("publisher") or "[No venue/source listed]"
    citations = candidate.get("cited_by_count")
    sources = candidate.get("metadata_sources") or [candidate.get("source")]
    source_text = ", ".join(source for source in sources if source) or "[unknown]"

    score_text = ""
    if candidate.get("score") is not None:
        score_text = f" [relevance: {candidate.get('score')}"
        if candidate.get("citation_score") is not None:
            score_text += f", cites: {candidate.get('citation_score')}"
        score_text += "]"

    retval = f"{prefix}{title}{score_text}\n"
    retval += f"   {authors} ({year})\n"
    retval += f"   {venue}\n"
    if citations is not None:
        retval += f"   citations: {citations}\n"
    if candidate.get("match_note"):
        retval += f"   match note: {candidate.get('match_note')}\n"
    retval += f"   metadata sources: {source_text}\n"
    retval += format_identifier_line("DOI", candidate.get("doi"))
    retval += format_identifier_line("arXiv", candidate.get("arxiv_id"))
    retval += format_identifier_line("OpenAlex", candidate.get("openalex_id"))
    if candidate.get("url"):
        retval += f"   URL: {candidate.get('url')}\n"
    return retval


def print_candidates(candidates: list[dict[str, Any]]) -> None:
    """Print numbered work candidates."""
    output = ""
    for i, candidate in enumerate(candidates[:MAX_DISPLAY_CANDIDATES], 1):
        output += serialize_candidate(candidate, i) + "\n"

    if len(candidates) > MAX_DISPLAY_CANDIDATES:
        output += f"... {len(candidates) - MAX_DISPLAY_CANDIDATES} more candidate(s) not shown.\n"

    page_text(output)


def print_dict(d: dict[str, Any]) -> None:
    for k, v in d.items():
        print(f"  {k}: {pformat(v)}")


def print_list_of_dicts(ld: list[dict[str, Any]]) -> None:
    for i in ld:
        print_dict(i)
        print()


def print_selected_work_metadata(candidate: dict[str, Any]) -> None:
    """Print the metadata already present on a selected candidate."""
    print("\n--- Candidate metadata ---")
    print_dict({
        "title": candidate.get("title", ""),
        "authors": candidate.get("authors", []),
        "year": candidate.get("year"),
        "venue": candidate.get("venue", ""),
        "publisher": candidate.get("publisher", ""),
        "type": candidate.get("type", ""),
        "citations": candidate.get("cited_by_count", 0),
        "metadata_sources": candidate.get("metadata_sources", []),
        "doi": candidate.get("doi"),
        "arxiv_id": candidate.get("arxiv_id"),
        "openalex_id": candidate.get("openalex_id"),
        "url": candidate.get("url", ""),
    })


def print_selected_work_details(candidate: dict[str, Any]) -> None:
    """Print structured metadata, identifiers, and BibTeX for a selected work."""
    title = candidate.get("title") or candidate.get("doi") or candidate.get("arxiv_id") or "Selected work"
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    print_selected_work_metadata(candidate)
    input("(Press Enter.)")

    doi = candidate.get("doi")
    if doi:
        print("\n--- Structured DOI metadata ---")
        metadata = get_best_structured_metadata(doi)
        if metadata is None:
            print(
                "No Crossref or DataCite metadata found. This may still be a "
                "valid DOI; it may simply be registered somewhere else or have "
                "limited public metadata."
            )
        else:
            print_dict(metadata)
        input("(Press Enter.)")

        print("\n--- ORCIDs from OpenAlex ---")
        orcids = get_orcids_from_openalex(doi)
        if not orcids:
            print("[]")
        else:
            print_list_of_dicts(orcids)
        input("(Press Enter.)")

        print("\n--- BibTeX from doi.org ---")
        bibtex = get_bibtex_from_doi(doi)
        if bibtex is None:
            print("No BibTeX returned by doi.org content negotiation.")
        else:
            print_bibtex(bibtex)
        input("(Press Enter.)")
    else:
        print("\n--- DOI-specific enrichment skipped ---")
        print("This selected work does not currently have a DOI in the merged metadata.")
        input("(Press Enter.)")

    print("\n--- Generated BibTeX-like entry from available metadata ---")
    generated = candidate_to_bibtex(candidate)
    print_bibtex(generated)
    input("(Press Enter to return to results list.)")

    print("=" * 60)


# Backward-compatible old name.
def print_selected_doi_details(doi: str) -> None:
    """Print details for a selected DOI."""
    candidate = get_candidate_from_doi(doi) or canonical_candidate({"doi": doi, "source": "user-supplied DOI"})
    print_selected_work_details(candidate)


# ---------------------------------------------------------
# BibTeX helpers
# ---------------------------------------------------------


def split_bibtex_fields(body: str) -> list[str]:
    """
    Split the inside of a BibTeX entry into top-level field assignments.

    This tries to split on commas that are not inside braces or quotes. It is
    intentionally simple, but good enough for ordinary doi.org BibTeX.
    """
    fields = []
    current = []
    brace_depth = 0
    in_quote = False
    escaped = False

    for ch in body:
        current.append(ch)

        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == '"' and brace_depth == 0:
            in_quote = not in_quote
            continue

        if not in_quote:
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth = max(0, brace_depth - 1)
            elif ch == "," and brace_depth == 0:
                field = "".join(current[:-1]).strip()
                if field:
                    fields.append(field)
                current = []

    final_field = "".join(current).strip()
    if final_field:
        fields.append(final_field)

    return fields


def clean_bibtex_value(value: str) -> str:
    """Remove simple surrounding BibTeX braces/quotes and tidy whitespace."""
    value = value.strip().rstrip(",")

    if len(value) >= 2:
        if value[0] == "{" and value[-1] == "}":
            value = value[1:-1]
        elif value[0] == '"' and value[-1] == '"':
            value = value[1:-1]

    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_bibtex_entry(bibtex: str) -> dict[str, Any] | None:
    """
    Parse a single BibTeX entry into a simple dictionary.

    Returns None if the entry does not look like a normal single BibTeX entry.
    """
    text = bibtex.strip()

    match = re.match(r"@(\w+)\s*\{\s*([^,]+)\s*,(.*)\}\s*$", text, re.DOTALL)
    if not match:
        return None

    entry_type = match.group(1).strip()
    cite_key = match.group(2).strip()
    body = match.group(3).strip()

    fields: dict[str, str] = {}

    for field_text in split_bibtex_fields(body):
        if "=" not in field_text:
            continue

        key, value = field_text.split("=", 1)
        key = key.strip().lower()
        fields[key] = clean_bibtex_value(value)

    return {
        "entry_type": entry_type,
        "cite_key": cite_key,
        "fields": fields,
    }


def print_bibtex(bibtex: str) -> None:
    """
    Print a BibTeX entry in a friendlier field-by-field format.

    Also prints the raw BibTeX afterward so the user can copy/paste it into
    BibTeX-aware tools.
    """
    parsed = parse_bibtex_entry(bibtex)

    if parsed is None:
        print("Could not parse BibTeX cleanly. Raw BibTeX:")
        print(bibtex.strip())
        return

    fields = parsed["fields"]

    print("BibTeX entry:")
    print(f"  type: {parsed['entry_type']}")
    print(f"  citation key: {parsed['cite_key']}")

    preferred_order = [
        "title",
        "author",
        "editor",
        "year",
        "journal",
        "booktitle",
        "publisher",
        "volume",
        "number",
        "pages",
        "doi",
        "eprint",
        "archiveprefix",
        "primaryclass",
        "url",
    ]

    printed = set()

    for key in preferred_order:
        if key in fields:
            print(f"  {key}: {fields[key]}")
            printed.add(key)

    for key in sorted(fields):
        if key not in printed:
            print(f"  {key}: {fields[key]}")

    print("\nRaw BibTeX:")
    print(bibtex.strip())


def bibtex_escape(value: Any) -> str:
    """Very small BibTeX escaping/tidying helper."""
    text = str(value or "")
    text = html.unescape(text)
    text = text.replace("{", "\\{").replace("}", "\\}")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_cite_key(candidate: dict[str, Any]) -> str:
    """Create a readable citation key from first author, year, and title."""
    authors = candidate.get("authors") or []
    if authors:
        author_part = author_lastish_name(authors[0]) or "work"
    else:
        author_part = "work"
    year = candidate.get("year") or "nd"

    # Keep title words in their original order. split_words() returns a set,
    # which is fine for matching but produces unstable and less readable keys.
    stop = {"a", "an", "and", "by", "for", "in", "of", "on", "the", "to", "with"}
    title_words = [
        word
        for word in normalize_for_match(candidate.get("title")).split()
        if len(word) > 2 and word not in stop
    ][:3]
    title_part = "".join(word[:12] for word in title_words) or "metadata"
    return re.sub(r"[^A-Za-z0-9_:-]", "", f"{author_part}{year}{title_part}")


def candidate_to_bibtex(candidate: dict[str, Any]) -> str:
    """Generate a conservative BibTeX-like entry from available candidate metadata."""
    entry_type = "article"
    if candidate.get("arxiv_id") and not candidate.get("doi"):
        entry_type = "misc"
    elif candidate.get("type") in {"book", "monograph"}:
        entry_type = "book"
    elif candidate.get("venue") and "proceed" in normalize_for_match(candidate.get("venue")):
        entry_type = "inproceedings"

    fields: list[tuple[str, Any]] = []
    if candidate.get("title"):
        fields.append(("title", candidate["title"]))
    if candidate.get("authors"):
        fields.append(("author", " and ".join(candidate["authors"])))
    if candidate.get("year"):
        fields.append(("year", candidate["year"]))

    venue = candidate.get("venue") or ""
    if venue and venue != "arXiv":
        if entry_type == "inproceedings":
            fields.append(("booktitle", venue))
        else:
            fields.append(("journal", venue))

    if candidate.get("publisher") and candidate.get("publisher") != "arXiv":
        fields.append(("publisher", candidate["publisher"]))
    if candidate.get("doi"):
        fields.append(("doi", candidate["doi"]))
    if candidate.get("arxiv_id"):
        fields.append(("eprint", candidate["arxiv_id"]))
        fields.append(("archivePrefix", "arXiv"))
        if candidate.get("arxiv_category"):
            fields.append(("primaryClass", candidate["arxiv_category"]))
    if candidate.get("url"):
        fields.append(("url", candidate["url"]))
    elif candidate.get("openalex_id"):
        fields.append(("url", candidate["openalex_id"]))

    cite_key = make_cite_key(candidate)
    lines = [f"@{entry_type}{{{cite_key},"]
    for key, value in fields:
        lines.append(f"  {key} = {{{bibtex_escape(value)}}},")
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------
# CLI Main Loop
# ---------------------------------------------------------


def main() -> None:
    """Run the scholarly metadata lookup CLI."""
    print("Welcome to the scholarly metadata lookup program!")

    search_data: dict[str, str | None] = {
        "title": None,
        "author": None,
        "year": None,
        "identifier": None,
    }

    while True:
        prompt = (
            "\nEnter [t]itle, [a]uthor, [y]ear, [i]dentifier, "
            "[l]ookup, [c]lear, or [q]uit: "
        )
        choice = input(prompt).strip().lower()

        if choice == "q":
            sys.exit(0)

        if choice == "c":
            search_data = {"title": None, "author": None, "year": None, "identifier": None}
            print_search_data(search_data)
            continue

        if choice == "t":
            value = input("title: ").strip()
            search_data["title"] = value or None
            search_data["identifier"] = None
            print_search_data(search_data)
            continue

        if choice == "a":
            value = input("author: ").strip()
            search_data["author"] = value or None
            search_data["identifier"] = None
            print_search_data(search_data)
            continue

        if choice == "y":
            value = input("year: ").strip()
            search_data["year"] = value or None
            search_data["identifier"] = None
            print_search_data(search_data)
            continue

        if choice == "i":
            value = input("identifier (DOI, arXiv ID/URL, or OpenAlex work ID/URL): ").strip()
            search_data = {"title": None, "author": None, "year": None, "identifier": value or None}
            print_search_data(search_data)
            continue

        if choice == "l":
            if not any(search_data.values()):
                print("Please enter a title, author, year, or identifier first.")
                continue

            print("Looking up work candidates...")
            results = get_work_candidates(**search_data)

            if not results:
                print("No work candidates found matching those criteria.")
                print_search_data(search_data)
                continue

            doi_count = sum(1 for result in results if result.get("doi"))
            arxiv_count = sum(1 for result in results if result.get("arxiv_id"))
            print(
                f"Found {len(results)} candidate work(s): "
                f"{doi_count} with DOI, {arxiv_count} with arXiv ID."
            )

            # Inner work-selection loop
            while True:
                print()
                print_candidates(results)

                work_choice = input(
                    "Choose work number (or [q]uit): "
                ).strip().lower()

                if work_choice == "q":
                    print_search_data(search_data)
                    break

                try:
                    idx = int(work_choice) - 1
                except ValueError:
                    print("Please enter a valid number or 'q'.")
                    continue

                if not (0 <= idx < min(len(results), MAX_DISPLAY_CANDIDATES)):
                    print("Invalid number. Please choose from the displayed list.")
                    continue

                selected = results[idx]
                print_selected_work_details(selected)

            continue

        print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
