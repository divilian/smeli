"""Metadata source lookups and cross-source orchestration."""
from __future__ import annotations

__all__ = [
    "get_metadata_from_crossref",
    "get_metadata_from_datacite",
    "get_best_structured_metadata",
    "get_bibtex_from_doi",
    "get_orcids_from_openalex",
    "get_orcids_from_crossref",
    "get_work_candidates_from_crossref",
    "get_work_candidates_from_openalex",
    "get_work_candidates_from_datacite",
    "get_work_candidates_from_arxiv",
    "get_candidate_from_openalex_id",
    "get_candidate_from_arxiv_id",
    "get_candidate_from_doi",
    "get_work_candidates_from_orcid",
    "get_work_candidates_from_identifier",
    "get_work_candidates",
    "get_doi_from_crossref",
    "get_doi_from_openalex",
]


import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote

from .config import _MAX_CANDIDATES_PER_SOURCE
from .http import _crossref_params, _fetch_json, _fetch_text, _openalex_params
from .normalize import (
    base_arxiv_id,
    clean_doi,
    extract_arxiv_id,
    extract_orcid,
    _first,
    _get_year_from_crossref,
    looks_like_doi,
    looks_like_orcid,
    orcid_url,
    _quote_doi_for_doi_org,
    _quote_doi_for_path,
    _split_words,
)
from .candidates import (
    _add_best_candidate_score,
    _add_candidate_score,
    _arxiv_entry_to_candidate,
    _author_names_from_crossref,
    _author_names_from_datacite,
    bibliographic_query,
    canonical_candidate,
    _candidate_matches,
    _candidate_matches_loose_query,
    _crossref_item_to_candidate,
    _datacite_record_to_candidate,
    _get_title_from_datacite,
    _get_type_from_datacite,
    merge_candidate_list,
    _openalex_item_to_candidate,
)


def get_metadata_from_crossref(doi: str) -> dict[str, Any] | None:
    """
    Fetch structured metadata for a DOI from Crossref.

    Important: this is a Crossref-specific lookup. It can fail for perfectly
    valid DOIs that are registered with another DOI registration agency.
    """
    doi = clean_doi(doi)
    if not doi:
        return None

    url = f"https://api.crossref.org/works/{_quote_doi_for_path(doi)}"
    data = _fetch_json(url, source="Crossref", params=_crossref_params())
    if not data:
        return None

    message = data.get("message")
    if not isinstance(message, dict):
        print("Crossref response did not contain the expected metadata block.")
        return None

    return {
        "source": "Crossref",
        "doi": message.get("DOI", doi),
        "title": _first(message.get("title"), ""),
        "authors": _author_names_from_crossref(message),
        "journal": _first(message.get("container-title"), ""),
        "publisher": message.get("publisher", ""),
        "citations": message.get("is-referenced-by-count", 0),
        "year": _get_year_from_crossref(message),
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

    url = f"https://api.datacite.org/dois/{_quote_doi_for_path(doi)}"
    data = _fetch_json(url, source="DataCite", quiet_statuses={404})
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
        "title": _get_title_from_datacite(attributes),
        "authors": _author_names_from_datacite(attributes),
        "journal": "",
        "publisher": attributes.get("publisher", ""),
        "citations": attributes.get("citationCount", 0),
        "year": attributes.get("publicationYear"),
        "type": _get_type_from_datacite(attributes),
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

    url = f"https://doi.org/{_quote_doi_for_doi_org(doi)}"
    headers = {"Accept": "application/x-bibtex"}
    return _fetch_text(url, source="doi.org BibTeX", headers=headers)

def get_orcids_from_openalex(doi: str) -> list[dict[str, str]]:
    """Extract author ORCIDs using OpenAlex."""
    doi = clean_doi(doi)
    if not doi:
        return []

    # OpenAlex accepts external IDs in the form doi:<bare-doi>.
    openalex_work_id = quote(f"doi:{doi}", safe=":")
    url = f"https://api.openalex.org/works/{openalex_work_id}"
    data = _fetch_json(url, source="OpenAlex", params=_openalex_params())
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

    url = f"https://api.crossref.org/works/{_quote_doi_for_path(doi)}"
    data = _fetch_json(url, source="Crossref", params=_crossref_params())
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

def get_work_candidates_from_crossref(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch work candidates from Crossref bibliographic search."""
    url = "https://api.crossref.org/works"

    params: dict[str, Any] = {
        "rows": _MAX_CANDIDATES_PER_SOURCE,
        "query.bibliographic": bibliographic_query(author, title, year),
    }
    if author:
        params["query.author"] = author
    if title:
        params["query.title"] = title
    if year:
        params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"

    data = _fetch_json(url, source="Crossref", params=_crossref_params(params))
    if not data:
        return []

    items = data.get("message", {}).get("items", [])
    matched = []

    for item in items:
        candidate = _crossref_item_to_candidate(item)
        if not candidate:
            continue
        if _candidate_matches(candidate, author=author, title=title, year=year, allow_loose_title=True):
            _add_candidate_score(candidate, author=author, title=title, year=year)
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
        "per-page": _MAX_CANDIDATES_PER_SOURCE,
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

    data = _fetch_json(url, source="OpenAlex", params=_openalex_params(params))
    if not data:
        return []

    items = data.get("results", [])
    matched = []

    for item in items:
        candidate = _openalex_item_to_candidate(item)
        if not candidate:
            continue
        if not _candidate_matches(candidate, author=author, title=title, year=year, allow_loose_title=False):
            continue
        _add_candidate_score(candidate, author=author, title=title, year=year)
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
        "page[size]": _MAX_CANDIDATES_PER_SOURCE,
        "query": query,
    }
    if year:
        params["publicationYear"] = str(year).strip()

    data = _fetch_json(url, source="DataCite", params=params)
    if not data:
        return []

    records = data.get("data", [])
    matched = []

    for record in records:
        candidate = _datacite_record_to_candidate(record)
        if not candidate:
            continue
        if _candidate_matches(candidate, author=author, title=title, year=year, allow_loose_title=True):
            _add_candidate_score(candidate, author=author, title=title, year=year)
            matched.append(candidate)

    return matched

def _arxiv_search_query(author: str | None, title: str | None, year: str | int | None) -> str:
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
        "search_query": _arxiv_search_query(author, title, year),
        "start": 0,
        "max_results": min(_MAX_CANDIDATES_PER_SOURCE, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    text = _fetch_text(url, source="arXiv", params=params)
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
        candidate = _arxiv_entry_to_candidate(entry)
        if not candidate:
            continue
        if _candidate_matches(candidate, author=author, title=title, year=year, allow_loose_title=True):
            _add_candidate_score(candidate, author=author, title=title, year=year)
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
    data = _fetch_json(url, source="OpenAlex", params=_openalex_params())
    if not data:
        return None

    return _openalex_item_to_candidate(data)

def get_candidate_from_arxiv_id(arxiv_id: str) -> dict[str, Any] | None:
    """Fetch a single candidate by arXiv ID."""
    arxiv_id = base_arxiv_id(extract_arxiv_id(arxiv_id) or arxiv_id)
    if not arxiv_id:
        return None

    url = "https://export.arxiv.org/api/query"
    params = {"id_list": arxiv_id, "max_results": 1}
    text = _fetch_text(url, source="arXiv", params=params)
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

    return _arxiv_entry_to_candidate(entry)

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
    openalex_data = _fetch_json(openalex_url, source="OpenAlex", params=_openalex_params())
    if openalex_data:
        openalex_candidate = _openalex_item_to_candidate(openalex_data)
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
            "url": f"https://doi.org/{_quote_doi_for_doi_org(doi)}",
        })

    merged = merge_candidate_list(candidates)
    return merged[0] if merged else None

def _get_work_candidates_from_openalex_loose(
    query: str,
    *,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch OpenAlex candidates using a broad all-fields fallback query."""
    if not query.strip():
        return []

    url = "https://api.openalex.org/works"
    params: dict[str, Any] = {
        "per-page": _MAX_CANDIDATES_PER_SOURCE,
        "search": query,
    }

    filters = []
    if year:
        year_text = str(year).strip()
        if re.fullmatch(r"\d{4}", year_text):
            filters.append(f"publication_year:{year_text}")
    if filters:
        params["filter"] = ",".join(filters)

    data = _fetch_json(url, source="OpenAlex", params=_openalex_params(params))
    if not data:
        return []

    matched = []
    for item in data.get("results", []):
        candidate = _openalex_item_to_candidate(item)
        if not candidate:
            continue
        if not _candidate_matches_loose_query(candidate, query, year=year):
            continue
        matched.append(candidate)

    return matched

def _get_work_candidates_from_crossref_loose(
    query: str,
    *,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch Crossref candidates using only broad bibliographic search."""
    if not query.strip():
        return []

    url = "https://api.crossref.org/works"
    params: dict[str, Any] = {
        "rows": _MAX_CANDIDATES_PER_SOURCE,
        "query.bibliographic": query,
    }
    if year:
        params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"

    data = _fetch_json(url, source="Crossref", params=_crossref_params(params))
    if not data:
        return []

    matched = []
    for item in data.get("message", {}).get("items", []):
        candidate = _crossref_item_to_candidate(item)
        if not candidate:
            continue
        if not _candidate_matches_loose_query(candidate, query, year=year):
            continue
        matched.append(candidate)

    return matched

def _get_work_candidates_from_datacite_loose(
    query: str,
    *,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch DataCite candidates using broad metadata search."""
    if not query.strip():
        return []

    url = "https://api.datacite.org/dois"
    params: dict[str, Any] = {
        "page[size]": _MAX_CANDIDATES_PER_SOURCE,
        "query": query,
    }
    if year:
        params["publicationYear"] = str(year).strip()

    data = _fetch_json(url, source="DataCite", params=params)
    if not data:
        return []

    matched = []
    for record in data.get("data", []):
        candidate = _datacite_record_to_candidate(record)
        if not candidate:
            continue
        if not _candidate_matches_loose_query(candidate, query, year=year):
            continue
        matched.append(candidate)

    return matched

def _arxiv_loose_search_query(query: str) -> str:
    """Build an arXiv all-fields query from significant normalized tokens."""
    terms = sorted(_split_words(query))
    if not terms:
        return "all:*"
    return " AND ".join(f'all:"{term}"' for term in terms)

def _get_work_candidates_from_arxiv_loose(
    query: str,
    *,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch arXiv candidates using a broad all-fields fallback query."""
    if not query.strip():
        return []

    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": _arxiv_loose_search_query(query),
        "start": 0,
        "max_results": min(_MAX_CANDIDATES_PER_SOURCE, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    text = _fetch_text(url, source="arXiv", params=params)
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
        candidate = _arxiv_entry_to_candidate(entry)
        if not candidate:
            continue
        if not _candidate_matches_loose_query(candidate, query, year=year):
            continue
        matched.append(candidate)

    return matched

def get_work_candidates_from_orcid(orcid: str) -> list[dict[str, Any]]:
    """Fetch work candidates for an author ORCID using OpenAlex."""
    bare_orcid = extract_orcid(orcid)
    if not bare_orcid:
        return []

    url = "https://api.openalex.org/works"
    params: dict[str, Any] = {
        "per-page": _MAX_CANDIDATES_PER_SOURCE,
        # OpenAlex works support filtering on the ORCID field nested inside
        # authorships.author. Use the bare ORCID here; using the canonical
        # https://orcid.org/... URL in an author-id filter can produce a 400.
        "filter": f"authorships.author.orcid:{bare_orcid}",
        "sort": "publication_date:desc",
    }

    data = _fetch_json(url, source="OpenAlex", params=_openalex_params(params))
    if not data:
        return []

    matched = []
    for item in data.get("results", []):
        candidate = _openalex_item_to_candidate(item)
        if not candidate:
            continue
        note = f"ORCID {bare_orcid}"
        candidate["_match_note"] = note
        candidate["match_note"] = note
        matched.append(candidate)

    return matched

def get_work_candidates_from_identifier(identifier: str) -> list[dict[str, Any]]:
    """Resolve a DOI, arXiv ID/URL, ORCID, or OpenAlex work ID/URL."""
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

    if looks_like_orcid(identifier):
        return get_work_candidates_from_orcid(identifier)

    if "openalex.org/" in identifier.lower() or re.fullmatch(r"W\d+", identifier.strip(), re.IGNORECASE):
        candidate = get_candidate_from_openalex_id(identifier)
        return [candidate] if candidate else []

    print("Identifier did not look like a DOI, arXiv ID/URL, ORCID or OpenAlex work ID/URL.")
    return []

def get_work_candidates(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
    identifier: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Search all configured metadata sources and return merged work candidates."""
    search_variants: list[dict[str, Any]] = [
        {"author": author, "title": title or query, "year": year},
    ]

    if identifier:
        candidates = get_work_candidates_from_identifier(identifier)
    elif query:
        candidates = []
        print("  OpenAlex...")
        candidates.extend(_get_work_candidates_from_openalex_loose(query, year=year))
        print("  Crossref...")
        candidates.extend(_get_work_candidates_from_crossref_loose(query, year=year))
        print("  DataCite...")
        candidates.extend(_get_work_candidates_from_datacite_loose(query, year=year))
        print("  arXiv...")
        candidates.extend(_get_work_candidates_from_arxiv_loose(query, year=year))
        for candidate in candidates:
            candidate["_match_note"] = "free-form query"
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
                loose_candidates.extend(_get_work_candidates_from_openalex_loose(loose_query, year=year))
                print("    Crossref...")
                loose_candidates.extend(_get_work_candidates_from_crossref_loose(loose_query, year=year))
                print("    DataCite...")
                loose_candidates.extend(_get_work_candidates_from_datacite_loose(loose_query, year=year))
                print("    arXiv...")
                loose_candidates.extend(_get_work_candidates_from_arxiv_loose(loose_query, year=year))
                for candidate in loose_candidates:
                    candidate["_match_note"] = "broad all-fields fallback"
                candidates.extend(loose_candidates)

    merged = merge_candidate_list(candidates)
    for candidate in merged:
        _add_best_candidate_score(candidate, search_variants)

    merged.sort(
        key=lambda c: (c.get("score") or 0, c.get("citation_score") or 0),
        reverse=True,
    )
    return merged

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
