"""Metadata source lookups and cross-source orchestration.

This module is the main networked public API for Smeli. It queries OpenAlex,
Crossref, DataCite, arXiv, and doi.org, then returns either structured metadata
dictionaries, ORCID lists, BibTeX strings, or Smeli candidate dictionaries.

Functions return ``None`` or an empty list when no useful result is found.
Expected misses are handled quietly where practical; real network and parsing
errors may print short diagnostic messages.
"""
from __future__ import annotations

__all__ = [
    "get_paper_candidates",
    "get_paper_candidates_from_identifier",
    "get_metadata",
    "get_orcids",
    "search_orcids",
    "get_candidate_from_doi",
    "get_candidate_from_arxiv_id",
    "get_candidate_from_openalex_id",
    "get_paper_candidates_from_orcid",
    "get_paper_candidates_from_openalex",
    "get_paper_candidates_from_crossref",
    "get_paper_candidates_from_datacite",
    "get_paper_candidates_from_arxiv",
    "get_metadata_from_crossref",
    "get_metadata_from_datacite",
    "get_bibtex_from_doi",
    "get_orcids_from_openalex",
    "get_orcids_from_crossref",
    "get_orcids_from_datacite",
    "get_doi_from_crossref",
    "get_doi_from_openalex",
]

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
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


def _emit_progress(progress: Callable[[str], None] | None, message: str) -> None:
    """Send a progress message to a caller-supplied callback, if any."""
    if progress is not None:
        progress(message)


def get_metadata_from_crossref(doi: str) -> dict[str, Any] | None:
    """Fetch structured metadata for a DOI from Crossref.

    Args:
        doi: A bare DOI, DOI URL, or DOI-like string.

    Returns:
        dict[str, Any] | None: A metadata dictionary with keys such as
            ``source``, ``doi``, ``title``, ``authors``, ``journal``,
            ``publisher``, ``citations``, ``year``, ``type``, and ``url``; or
            ``None`` if Crossref has no usable record.

    Notes:
        This is a Crossref-specific lookup. It can fail for valid DOIs
        registered with another DOI registration agency.
    """
    doi = clean_doi(doi)
    if not doi:
        return None

    url = f"https://api.crossref.org/works/{_quote_doi_for_path(doi)}"
    data = _fetch_json(url, source="Crossref", params=_crossref_params(), quiet_statuses={404})
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
    """Fetch structured metadata for a DOI from DataCite.

    Args:
        doi: A bare DOI, DOI URL, or DOI-like string.

    Returns:
        dict[str, Any] | None: A metadata dictionary with keys such as
            ``source``, ``doi``, ``title``, ``authors``, ``journal``,
            ``publisher``, ``citations``, ``year``, ``type``, and ``url``; or
            ``None`` if DataCite has no usable record.

    Notes:
        DataCite is a separate DOI registration agency from Crossref. It is
        often useful for datasets, software, preprints, and repository items.
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

def _metadata_from_candidate(candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a structured metadata dictionary from a Smeli candidate."""
    if not candidate:
        return None

    metadata: dict[str, Any] = {
        "source": candidate.get("source", ""),
        "doi": candidate.get("doi"),
        "title": candidate.get("title", ""),
        "authors": candidate.get("authors", []),
        "journal": candidate.get("venue", ""),
        "publisher": candidate.get("publisher", ""),
        "citations": candidate.get("cited_by_count", 0),
        "year": candidate.get("year"),
        "type": candidate.get("type", ""),
        "url": candidate.get("url", ""),
    }
    if candidate.get("arxiv_id"):
        metadata["arxiv_id"] = candidate["arxiv_id"]
    if candidate.get("openalex_id"):
        metadata["openalex_id"] = candidate["openalex_id"]
    return metadata

def _get_candidate_from_openalex_doi(doi: str) -> dict[str, Any] | None:
    """Fetch a Smeli candidate for a DOI directly from OpenAlex."""
    doi = clean_doi(doi)
    if not doi:
        return None

    openalex_work_id = quote(f"doi:{doi}", safe=":")
    url = f"https://api.openalex.org/works/{openalex_work_id}"
    data = _fetch_json(url, source="OpenAlex", params=_openalex_params(), quiet_statuses={404})
    if not data:
        return None

    return _openalex_item_to_candidate(data)

def get_metadata(identifier: str | None) -> dict[str, Any] | None:
    """Fetch structured metadata for a DOI, arXiv ID, or OpenAlex Work ID.

    Args:
        identifier: A DOI, DOI URL, arXiv ID/URL, or OpenAlex Work ID/URL.

    Returns:
        dict[str, Any] | None: A source-agnostic metadata dictionary when Smeli
            finds usable metadata, or ``None`` when no configured source has a
            usable record.

    Notes:
        DOI lookup tries Crossref first, then DataCite, then OpenAlex. arXiv and
        OpenAlex identifiers are resolved through their native APIs. Source-
        specific helpers remain available when callers deliberately want a
        particular service.
    """
    value = str(identifier or "").strip()
    if not value:
        return None

    if looks_like_doi(value):
        doi = clean_doi(value)
        metadata = get_metadata_from_crossref(doi)
        if metadata is not None:
            return metadata

        metadata = get_metadata_from_datacite(doi)
        if metadata is not None:
            return metadata

        return _metadata_from_candidate(_get_candidate_from_openalex_doi(doi))

    arxiv_id = extract_arxiv_id(value)
    if arxiv_id:
        return _metadata_from_candidate(get_candidate_from_arxiv_id(arxiv_id))

    if "openalex.org/" in value.lower() or re.fullmatch(r"W\d+", value, re.IGNORECASE):
        return _metadata_from_candidate(get_candidate_from_openalex_id(value))

    return None

def get_bibtex_from_doi(doi: str) -> str | None:
    """Retrieve BibTeX from doi.org content negotiation.

    Args:
        doi: A bare DOI, DOI URL, or DOI-like string.

    Returns:
        str | None: A raw BibTeX string from the DOI resolver, or ``None`` when
            no BibTeX is returned.

    Notes:
        This goes through the DOI resolver rather than Crossref directly, so it
        may succeed for DOIs outside Crossref's registry.
    """
    doi = clean_doi(doi)
    if not doi:
        return None

    url = f"https://doi.org/{_quote_doi_for_doi_org(doi)}"
    headers = {"Accept": "application/x-bibtex"}
    return _fetch_text(url, source="doi.org BibTeX", headers=headers)

def _add_orcid_id(orcids: list[str], value: Any) -> None:
    """Append a normalized ORCID iD if it is present and not already listed."""
    orcid = extract_orcid(value)
    if orcid and orcid not in orcids:
        orcids.append(orcid)

def _orcid_ids_from_nested_value(value: Any) -> list[str]:
    """Return all normalized ORCID iDs found in a nested value."""
    orcids: list[str] = []
    if isinstance(value, str):
        _add_orcid_id(orcids, value)
    elif isinstance(value, Mapping):
        for item in value.values():
            for orcid in _orcid_ids_from_nested_value(item):
                _add_orcid_id(orcids, orcid)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            for orcid in _orcid_ids_from_nested_value(item):
                _add_orcid_id(orcids, orcid)
    return orcids

def _orcid_ids_from_records(records: list[dict[str, str]] | list[str]) -> list[str]:
    """Return normalized ORCID iDs from source-specific ORCID records."""
    orcids: list[str] = []
    for record in records:
        if isinstance(record, Mapping):
            _add_orcid_id(orcids, record.get("orcid"))
        else:
            _add_orcid_id(orcids, record)
    return orcids

def get_orcids(value: Any | None) -> list[str]:
    """Return normalized ORCID iDs from an identifier or metadata record.

    Args:
        value: A DOI, ORCID iD/URL, or a nested metadata/candidate record that
            may contain ORCID values.

    Returns:
        list[str]: Normalized bare ORCID iDs, deduplicated in discovery order.

    Notes:
        DOI lookup checks OpenAlex, Crossref, and DataCite. Source-specific
        helpers return richer ``{"name": ..., "orcid": ...}`` records; this
        high-level helper returns just the normalized identifiers.
    """
    if value is None:
        return []

    if not isinstance(value, str):
        return _orcid_ids_from_nested_value(value)

    text = value.strip()
    if not text:
        return []

    if looks_like_orcid(text):
        orcid = extract_orcid(text)
        return [orcid] if orcid else []

    if not looks_like_doi(text):
        metadata = get_metadata(text)
        return _orcid_ids_from_nested_value(metadata) if metadata else []

    doi = clean_doi(text)
    orcids: list[str] = []
    for records in (
        get_orcids_from_openalex(doi),
        get_orcids_from_crossref(doi),
        get_orcids_from_datacite(doi),
    ):
        for orcid in _orcid_ids_from_records(records):
            _add_orcid_id(orcids, orcid)
    return orcids

def _text_matches_affiliation(texts: list[str], affiliation: str | None) -> bool:
    """Return whether affiliation text matches a caller-supplied fragment."""
    if not affiliation:
        return True
    needle = affiliation.strip().casefold()
    if not needle:
        return True
    return any(needle in text.casefold() for text in texts)


def _openalex_author_affiliations(author: Mapping[str, Any]) -> list[str]:
    """Return institution display names from an OpenAlex author record."""
    affiliations: list[str] = []

    def add_name(value: Any) -> None:
        if isinstance(value, str):
            name = value.strip()
        elif isinstance(value, Mapping):
            name = str(value.get("display_name") or "").strip()
        else:
            name = ""
        if name and name not in affiliations:
            affiliations.append(name)

    for institution in author.get("last_known_institutions") or []:
        add_name(institution)

    add_name(author.get("last_known_institution"))

    for affiliation in author.get("affiliations") or []:
        if not isinstance(affiliation, Mapping):
            continue
        institution = affiliation.get("institution")
        add_name(institution)

    return affiliations


def _openalex_author_to_orcid_result(author: Mapping[str, Any]) -> dict[str, Any] | None:
    """Convert an OpenAlex author record to a Smeli ORCID search result."""
    orcid = extract_orcid(author.get("orcid"))
    if not orcid:
        return None

    affiliations = _openalex_author_affiliations(author)
    result: dict[str, Any] = {
        "name": str(author.get("display_name") or "").strip(),
        "orcid": orcid,
        "orcid_url": orcid_url(orcid),
        "openalex_id": author.get("id", ""),
        "affiliation": affiliations[0] if affiliations else "",
        "affiliations": affiliations,
        "works_count": author.get("works_count", 0),
        "cited_by_count": author.get("cited_by_count", 0),
        "source": "OpenAlex",
    }
    relevance = author.get("relevance_score")
    if isinstance(relevance, (int, float)):
        result["relevance"] = relevance
    return result


def search_orcids(
    name: str | None,
    affiliation: str | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Search for author ORCID iDs by partial author name.

    Args:
        name: Author name or name fragment to search for.
        affiliation: Optional institution or affiliation fragment used for
            local filtering of returned author candidates.
        max_results: Maximum number of ORCID-bearing candidate records to
            return.

    Returns:
        list[dict[str, Any]]: Candidate author records with keys such as
            ``name``, ``orcid``, ``orcid_url``, ``openalex_id``,
            ``affiliation``, ``affiliations``, ``works_count``,
            ``cited_by_count``, ``source``, and sometimes ``relevance``.

    Notes:
        This searches OpenAlex author records. It returns candidate people, not
        papers, and deliberately excludes author records without ORCID iDs.
    """
    query = str(name or "").strip()
    if not query:
        return []

    try:
        requested = int(max_results)
    except (TypeError, ValueError):
        requested = 10
    requested = max(1, min(requested, _MAX_CANDIDATES_PER_SOURCE))

    # Fetch a few extra records when affiliation filtering is requested, since
    # some high-ranked name matches may be filtered out locally.
    per_page = requested
    if affiliation and affiliation.strip():
        per_page = min(_MAX_CANDIDATES_PER_SOURCE, requested * 3)

    url = "https://api.openalex.org/authors"
    params: dict[str, Any] = {
        "search": query,
        "per-page": per_page,
    }
    data = _fetch_json(url, source="OpenAlex", params=_openalex_params(params))
    if not data:
        return []

    results: list[dict[str, Any]] = []
    seen_orcids: set[str] = set()
    for author in data.get("results", []):
        if not isinstance(author, Mapping):
            continue
        result = _openalex_author_to_orcid_result(author)
        if not result:
            continue
        orcid = result["orcid"]
        if orcid in seen_orcids:
            continue
        if not _text_matches_affiliation(result.get("affiliations", []), affiliation):
            continue
        seen_orcids.add(orcid)
        results.append(result)
        if len(results) >= requested:
            break

    return results


def get_orcids_from_openalex(doi: str) -> list[dict[str, str]]:
    """Extract author ORCIDs for a DOI using OpenAlex.

Args:
    doi: A bare DOI, DOI URL, or DOI-like string.

Returns:
    list[dict[str, str]]: A list of dictionaries with ``name`` and ``orcid``
        keys, or an empty list when OpenAlex has no ORCID data for the paper.
"""
    doi = clean_doi(doi)
    if not doi:
        return []

    # OpenAlex accepts external IDs in the form doi:<bare-doi>.
    openalex_work_id = quote(f"doi:{doi}", safe=":")
    url = f"https://api.openalex.org/works/{openalex_work_id}"
    data = _fetch_json(url, source="OpenAlex", params=_openalex_params(), quiet_statuses={404})
    if not data:
        return []

    orcids = []
    for authorship in data.get("authorships", []):
        author = authorship.get("author", {})
        orcid_url = author.get("orcid")

        # If OpenAlex has an ORCID for this author, it will usually be a full URL.
        if orcid_url:
            name = author.get("display_name", "").strip()
            orcid_id = extract_orcid(orcid_url)
            if orcid_id:
                orcids.append({"name": name, "orcid": orcid_id})

    return orcids

def get_orcids_from_crossref(doi: str) -> list[dict[str, str]]:
    """Extract author ORCIDs from Crossref metadata.

    Args:
        doi: A bare DOI, DOI URL, or DOI-like string.

    Returns:
        list[dict[str, str]]: A list of dictionaries with ``name`` and
            ``orcid`` keys, or an empty list when Crossref has no ORCID data for
            the paper.

    Notes:
        Crossref ORCID coverage depends on what the publisher supplied.
    """
    doi = clean_doi(doi)
    if not doi:
        return []

    url = f"https://api.crossref.org/works/{_quote_doi_for_path(doi)}"
    data = _fetch_json(url, source="Crossref", params=_crossref_params(), quiet_statuses={404})
    if not data:
        return []

    authors = data.get("message", {}).get("author", [])
    orcids = []
    for author in authors:
        # If the publisher provided an ORCID, it will be here.
        if "ORCID" in author:
            name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            orcid_id = extract_orcid(author["ORCID"])
            if orcid_id:
                orcids.append({"name": name, "orcid": orcid_id})

    return orcids

def get_orcids_from_datacite(doi: str) -> list[dict[str, str]]:
    """Extract author ORCIDs from DataCite metadata.

    Args:
        doi: A bare DOI, DOI URL, or DOI-like string.

    Returns:
        list[dict[str, str]]: A list of dictionaries with ``name`` and
            ``orcid`` keys, or an empty list when DataCite has no ORCID data for
            the paper.

    Notes:
        DataCite ORCID coverage is common for repository and dataset records,
        but still depends on what the depositing source supplied.
    """
    doi = clean_doi(doi)
    if not doi:
        return []

    url = f"https://api.datacite.org/dois/{_quote_doi_for_path(doi)}"
    data = _fetch_json(url, source="DataCite", quiet_statuses={404})
    if not data:
        return []

    attributes = data.get("data", {}).get("attributes", {})
    creators = attributes.get("creators", []) if isinstance(attributes, dict) else []
    orcids: list[dict[str, str]] = []
    seen: set[str] = set()

    for creator in creators:
        if not isinstance(creator, dict):
            continue
        name = creator.get("name") or f"{creator.get('givenName', '')} {creator.get('familyName', '')}".strip()
        for orcid_id in _orcid_ids_from_nested_value(creator):
            if orcid_id in seen:
                continue
            seen.add(orcid_id)
            orcids.append({"name": name, "orcid": orcid_id})

    return orcids

def get_paper_candidates_from_crossref(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch paper candidates from Crossref bibliographic search.

Args:
    author: Optional author name or fragment.
    title: Optional title or title fragment.
    year: Optional publication year.

Returns:
    list[dict[str, Any]]: A list of Smeli candidate dictionaries from Crossref
        that pass local matching.
"""
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

def get_paper_candidates_from_openalex(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch paper candidates from OpenAlex.

    Args:
        author: Optional author name or fragment.
        title: Optional title or title fragment.
        year: Optional publication year.

    Returns:
        list[dict[str, Any]]: A list of Smeli candidate dictionaries from
            OpenAlex that pass local matching.

    Notes:
        DOI-less OpenAlex records are deliberately retained.
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

def get_paper_candidates_from_datacite(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch paper candidates from DataCite metadata search.

Args:
    author: Optional author name or fragment.
    title: Optional title or title fragment.
    year: Optional publication year.

Returns:
    list[dict[str, Any]]: A list of Smeli candidate dictionaries from DataCite
        that pass local matching.
"""
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

def get_paper_candidates_from_arxiv(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Fetch paper candidates from the arXiv Atom API.

Args:
    author: Optional author name or fragment.
    title: Optional title or title fragment.
    year: Optional publication year used for local filtering.

Returns:
    list[dict[str, Any]]: A list of Smeli candidate dictionaries from arXiv that
        pass local matching.
"""
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
    """Fetch a single candidate by OpenAlex Work ID or URL.

Args:
    openalex_id: An OpenAlex Work ID such as ``"W2741809807"`` or a full
        ``openalex.org`` Work URL.

Returns:
    dict[str, Any] | None: A Smeli candidate dictionary, or ``None`` when the
        OpenAlex record cannot be fetched or converted.
"""
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
    """Fetch a single candidate by arXiv ID.

Args:
    arxiv_id: A bare arXiv ID, ``arXiv:``-prefixed ID, or arXiv URL.

Returns:
    dict[str, Any] | None: A Smeli candidate dictionary, or ``None`` when arXiv
        has no matching entry.
"""
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
    """Build a single candidate around a known DOI.

Args:
    doi: A bare DOI, DOI URL, or DOI-like string.

Returns:
    dict[str, Any] | None: A merged Smeli candidate dictionary enriched from
        Crossref, DataCite, and OpenAlex where available. If no external
        metadata is found for a valid DOI, returns a minimal DOI-only candidate.
"""
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
    openalex_candidate = _get_candidate_from_openalex_doi(doi)
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

def _get_paper_candidates_from_openalex_loose(
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

def _get_paper_candidates_from_crossref_loose(
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

def _get_paper_candidates_from_datacite_loose(
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

def _get_paper_candidates_from_arxiv_loose(
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

def get_paper_candidates_from_orcid(orcid: str) -> list[dict[str, Any]]:
    """Fetch paper candidates for an author ORCID using OpenAlex.

Args:
    orcid: A bare ORCID iD or ORCID URL.

Returns:
    list[dict[str, Any]]: A list of Smeli candidate dictionaries, sorted by
        OpenAlex publication date descending before later Smeli ranking/merging.

Notes:
    ORCID identifies a person, not a paper, so this function returns a list of
    papers. OpenAlex may return no papers for a valid ORCID when its author
    links lack that ORCID.
"""
    bare_orcid = extract_orcid(orcid)
    if not bare_orcid:
        return []

    url = "https://api.openalex.org/works"
    params: dict[str, Any] = {
        "per-page": _MAX_CANDIDATES_PER_SOURCE,
        # OpenAlex Works support filtering on the ORCID field nested inside
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

def get_paper_candidates_from_identifier(identifier: str) -> list[dict[str, Any]]:
    """Resolve a DOI, arXiv ID/URL, ORCID, or OpenAlex Work ID/URL.

Args:
    identifier: A scholarly identifier or resolver URL.

Returns:
    list[dict[str, Any]]: A list of Smeli candidate dictionaries. Paper
        identifiers usually return zero or one candidate. ORCID identifiers may
        return many candidates because they identify an author/person rather
        than a paper.
"""
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
        return get_paper_candidates_from_orcid(identifier)

    if "openalex.org/" in identifier.lower() or re.fullmatch(r"W\d+", identifier.strip(), re.IGNORECASE):
        candidate = get_candidate_from_openalex_id(identifier)
        return [candidate] if candidate else []

    print("Identifier did not look like a DOI, arXiv ID/URL, ORCID or OpenAlex Work ID/URL.")
    return []

def get_paper_candidates(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
    identifier: str | None = None,
    query: str | None = None,
    *,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Search all configured metadata sources and return merged candidates.

Args:
    author: Optional author name or fragment for fielded search.
    title: Optional title or title fragment for fielded search.
    year: Optional publication year for filtering/scoring.
    identifier: Optional DOI, arXiv ID/URL, ORCID, or OpenAlex Work ID/URL. When
        supplied, identifier resolution takes precedence over fielded search.
    query: Optional free-form bibliographic query. Used when no identifier is
        supplied.
    progress: Optional callback for source-level progress messages. The CLI
        passes ``print`` here; ordinary Python API calls are quiet by default.

Returns:
    list[dict[str, Any]]: A score-sorted list of merged Smeli candidate
        dictionaries. Duplicate paper records from multiple sources are
        collapsed and annotated with ``metadata_sources``.

Notes:
    This is the highest-level public lookup API. It does not print during
    ordinary Python API use unless a progress callback is supplied.
"""
    search_variants: list[dict[str, Any]] = [
        {"author": author, "title": title or query, "year": year},
    ]

    if identifier:
        candidates = get_paper_candidates_from_identifier(identifier)
    elif query:
        candidates = []
        _emit_progress(progress, "  OpenAlex...")
        candidates.extend(_get_paper_candidates_from_openalex_loose(query, year=year))
        _emit_progress(progress, "  Crossref...")
        candidates.extend(_get_paper_candidates_from_crossref_loose(query, year=year))
        _emit_progress(progress, "  DataCite...")
        candidates.extend(_get_paper_candidates_from_datacite_loose(query, year=year))
        _emit_progress(progress, "  arXiv...")
        candidates.extend(_get_paper_candidates_from_arxiv_loose(query, year=year))
        for candidate in candidates:
            candidate["_match_note"] = "free-form query"
    else:
        candidates = []
        _emit_progress(progress, "  OpenAlex...")
        candidates.extend(get_paper_candidates_from_openalex(author=author, title=title, year=year))
        _emit_progress(progress, "  Crossref...")
        candidates.extend(get_paper_candidates_from_crossref(author=author, title=title, year=year))
        _emit_progress(progress, "  DataCite...")
        candidates.extend(get_paper_candidates_from_datacite(author=author, title=title, year=year))
        _emit_progress(progress, "  arXiv...")
        candidates.extend(get_paper_candidates_from_arxiv(author=author, title=title, year=year))

        # If title+author matching found nothing, try the most common data-entry
        # mistake: the user put the author in the title field and title words in
        # the author field. This is cheap and catches searches like
        # title="starnini", author="opinion dynamics".
        if not candidates and title and author:
            _emit_progress(progress, "  No strict fielded matches. Trying title/author swapped...")
            swapped = {"author": title, "title": author, "year": year, "_match_note": "title/author swapped"}
            search_variants.append(swapped)
            swapped_candidates: list[dict[str, Any]] = []
            _emit_progress(progress, "    OpenAlex...")
            swapped_candidates.extend(get_paper_candidates_from_openalex(author=title, title=author, year=year))
            _emit_progress(progress, "    Crossref...")
            swapped_candidates.extend(get_paper_candidates_from_crossref(author=title, title=author, year=year))
            _emit_progress(progress, "    DataCite...")
            swapped_candidates.extend(get_paper_candidates_from_datacite(author=title, title=author, year=year))
            _emit_progress(progress, "    arXiv...")
            swapped_candidates.extend(get_paper_candidates_from_arxiv(author=title, title=author, year=year))
            for candidate in swapped_candidates:
                candidate["_match_note"] = "title/author swapped"
            candidates.extend(swapped_candidates)

        # Last resort: treat all supplied words as a broad bibliographic query,
        # then require those words to appear somewhere in title/authors/venue/IDs.
        # This protects the CLI from brittle API field semantics.
        if not candidates:
            loose_query = bibliographic_query(author, title, year=None)
            if loose_query:
                _emit_progress(progress, "  No fielded matches. Trying broad all-fields fallback...")
                search_variants.append({"author": None, "title": loose_query, "year": year, "_match_note": "broad all-fields fallback"})
                loose_candidates: list[dict[str, Any]] = []
                _emit_progress(progress, "    OpenAlex...")
                loose_candidates.extend(_get_paper_candidates_from_openalex_loose(loose_query, year=year))
                _emit_progress(progress, "    Crossref...")
                loose_candidates.extend(_get_paper_candidates_from_crossref_loose(loose_query, year=year))
                _emit_progress(progress, "    DataCite...")
                loose_candidates.extend(_get_paper_candidates_from_datacite_loose(loose_query, year=year))
                _emit_progress(progress, "    arXiv...")
                loose_candidates.extend(_get_paper_candidates_from_arxiv_loose(loose_query, year=year))
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
    """Return Crossref paper candidates that have DOIs.

Args:
    author: Optional author name or fragment.
    title: Optional title or title fragment.
    year: Optional publication year.

Returns:
    list[dict[str, Any]]: Crossref candidate dictionaries filtered to records
        with a DOI.

Notes:
    This is a compatibility/convenience helper from Smeli's DOI-focused origins.
    New code usually wants `get_paper_candidates_from_crossref()` or
    `get_paper_candidates()` instead.
"""
    return [
        candidate
        for candidate in get_paper_candidates_from_crossref(author=author, title=title, year=year)
        if candidate.get("doi")
    ]

def get_doi_from_openalex(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """Return OpenAlex paper candidates that have DOIs.

Args:
    author: Optional author name or fragment.
    title: Optional title or title fragment.
    year: Optional publication year.

Returns:
    list[dict[str, Any]]: OpenAlex candidate dictionaries filtered to records
        with a DOI.

Notes:
    This is a compatibility/convenience helper from Smeli's DOI-focused origins.
    New code usually wants `get_paper_candidates_from_openalex()` or
    `get_paper_candidates()` instead.
"""
    return [
        candidate
        for candidate in get_paper_candidates_from_openalex(author=author, title=title, year=year)
        if candidate.get("doi")
    ]
