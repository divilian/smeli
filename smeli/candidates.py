"""Candidate conversion, scoring, and merging helpers.

A *candidate* is Smeli's normal work-record dictionary. It may represent a
journal article, conference paper, arXiv preprint, dataset, software record, or
other scholarly work. Common keys include ``title``, ``authors``, ``year``,
``venue``, ``publisher``, ``doi``, ``arxiv_id``, ``openalex_id``, ``url``,
``cited_by_count``, ``metadata_sources``, ``score``, and ``citation_score``.

The public functions in this module are pure local helpers: they do not perform
network requests.
"""
from __future__ import annotations

__all__ = [
    "canonical_candidate",
    "candidate_score",
    "candidates_are_same",
    "merge_candidates",
    "merge_candidate_list",
    "bibliographic_query",
]


import html
import re
import xml.etree.ElementTree as ET
from typing import Any

from .normalize import (
    _author_lastish_name,
    _author_overlap,
    base_arxiv_id,
    clean_doi,
    _contains_normalized,
    extract_arxiv_id,
    _find_arxiv_id_in_mapping,
    _first,
    _get_year_from_crossref,
    _get_year_from_date,
    make_arxiv_url,
    _maybe_int,
    _normalize_for_match,
    _quote_doi_for_doi_org,
    _split_words,
    _title_similarity,
)


def _author_names_from_crossref(item: dict[str, Any]) -> list[str]:
    """Return author display names from a Crossref item."""
    names = []
    for author in item.get("author", []):
        name = f"{author.get('given', '')} {author.get('family', '')}".strip()
        if name:
            names.append(name)
    return names

def _author_names_from_openalex(item: dict[str, Any]) -> list[str]:
    """Return author display names from an OpenAlex item."""
    names = []
    for authorship in item.get("authorships", []):
        name = authorship.get("author", {}).get("display_name", "")
        if name:
            names.append(name)
    return names

def _author_names_from_datacite(attributes: dict[str, Any]) -> list[str]:
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

def _get_title_from_datacite(attributes: dict[str, Any]) -> str:
    """Return the first title from a DataCite metadata record."""
    for title in attributes.get("titles", []):
        title_text = title.get("title", "").strip()
        if title_text:
            return html.unescape(title_text)
    return ""

def _get_type_from_datacite(attributes: dict[str, Any]) -> str:
    """Return the most useful type string from a DataCite metadata record."""
    types = attributes.get("types") or {}
    return types.get("resourceType") or types.get("resourceTypeGeneral") or ""

def canonical_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized copy of a candidate dictionary.

Args:
    candidate: A partial Smeli candidate record. Missing optional fields are
        allowed.

Returns:
    A new dictionary with normalized DOI/arXiv identifiers, default values for
    common optional fields, a ``metadata_sources`` list, and a best-effort
    landing ``url`` when an identifier is available.

Notes:
    The input dictionary is copied before modification.
"""
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
        candidate["url"] = f"https://doi.org/{_quote_doi_for_doi_org(candidate['doi'])}"

    return candidate

def _crossref_item_to_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a Crossref result item into a work candidate dictionary."""
    title = _first(item.get("title"), "")
    doi = clean_doi(item.get("DOI"))
    if not title and not doi:
        return None

    candidate = {
        "doi": doi,
        "arxiv_id": extract_arxiv_id(item.get("URL", "")),
        "openalex_id": "",
        "title": title,
        "year": _get_year_from_crossref(item),
        "authors": _author_names_from_crossref(item),
        "venue": _first(item.get("container-title"), ""),
        "publisher": item.get("publisher", ""),
        "cited_by_count": item.get("is-referenced-by-count", 0),
        "type": item.get("type", ""),
        "source": "Crossref",
        "id": item.get("URL", ""),
        "url": item.get("URL", ""),
    }
    return canonical_candidate(candidate)

def _best_openalex_url(item: dict[str, Any]) -> str:
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

def _openalex_item_to_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert an OpenAlex work item into a work candidate dictionary."""
    ids = item.get("ids") or {}
    doi = clean_doi(item.get("doi") or ids.get("doi"))

    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    url = _best_openalex_url(item)
    arxiv_id = _find_arxiv_id_in_mapping(item)

    title = item.get("title", "") or item.get("display_name", "") or ""
    if not title and not doi and not arxiv_id:
        return None

    candidate = {
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": item.get("id", ""),
        "title": title,
        "year": item.get("publication_year"),
        "authors": _author_names_from_openalex(item),
        "venue": source.get("display_name", "") or "",
        "publisher": source.get("host_organization_name", "") or "",
        "cited_by_count": item.get("cited_by_count", 0),
        "type": item.get("type", ""),
        "source": "OpenAlex",
        "id": item.get("id", ""),
        "url": url,
    }
    return canonical_candidate(candidate)

def _datacite_record_to_candidate(record: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a DataCite DOI record into a work candidate dictionary."""
    attributes = record.get("attributes") or {}
    doi = clean_doi(attributes.get("doi") or record.get("id"))
    title = _get_title_from_datacite(attributes)
    if not title and not doi:
        return None

    url = attributes.get("url") or ""
    candidate = {
        "doi": doi,
        "arxiv_id": extract_arxiv_id(url) or _find_arxiv_id_in_mapping(attributes),
        "openalex_id": "",
        "title": title,
        "year": attributes.get("publicationYear"),
        "authors": _author_names_from_datacite(attributes),
        "venue": attributes.get("container", {}).get("title", "") if isinstance(attributes.get("container"), dict) else "",
        "publisher": attributes.get("publisher", ""),
        "cited_by_count": attributes.get("citationCount", 0),
        "type": _get_type_from_datacite(attributes),
        "source": "DataCite",
        "id": record.get("id", ""),
        "url": url,
    }
    return canonical_candidate(candidate)

def _arxiv_entry_to_candidate(entry: ET.Element) -> dict[str, Any] | None:
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
    year = _get_year_from_date(text("atom:published"))

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

def _candidate_matches(
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
            query_words = _split_words(title)
            candidate_words = _split_words(candidate.get("title"))
            if query_words and not query_words.intersection(candidate_words):
                return False
        elif not _contains_normalized(candidate.get("title"), title):
            return False

    if author:
        authors = candidate.get("authors", [])
        if not any(_contains_normalized(name, author) for name in authors):
            return False

    if year:
        if str(candidate.get("year")) != str(year).strip():
            return False

    return True

def _candidate_search_text(candidate: dict[str, Any]) -> str:
    """Return a broad text blob for loose all-fields matching."""
    parts: list[str] = []
    for key in ("title", "venue", "publisher", "type", "doi", "arxiv_id", "openalex_id", "url"):
        value = candidate.get(key)
        if value:
            parts.append(str(value))
    parts.extend(str(name) for name in candidate.get("authors", []) if name)
    return " ".join(parts)

def _candidate_matches_loose_query(
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

    query_words = _split_words(query)
    if not query_words:
        return True

    candidate_words = _split_words(_candidate_search_text(candidate))
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
    """Return a local relevance score for a work candidate.

    Args:
        candidate: A Smeli candidate dictionary.
        author: Optional author name or fragment supplied by the user.
        title: Optional title or title fragment supplied by the user.
        year: Optional publication year supplied by the user.

    Returns:
        A ``(score, citation_bonus)`` tuple. ``score`` reflects local
        bibliographic relevance; ``citation_bonus`` is a weak tie-breaker
        derived from citation count.

    Notes:
        The score is intentionally heuristic. It is useful for ranking plausible
        candidates, not for measuring scholarly relevance in an academic sense.
    """
    score = 0

    candidate_title = _normalize_for_match(candidate.get("title"))
    query_title = _normalize_for_match(title)

    if query_title:
        similarity = _title_similarity(candidate_title, query_title)
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
            shared = _split_words(candidate_title).intersection(_split_words(query_title))
            score += min(35, len(shared) * 8)

        # Prefer tight title matches over much longer titles that merely
        # contain the query as a substring.
        title_word_gap = abs(
            len(candidate_title.split()) - len(query_title.split())
        )
        score -= min(title_word_gap, 25)

    if author:
        query_author = _normalize_for_match(author)
        candidate_authors = [
            _normalize_for_match(name)
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

def _add_candidate_score(
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

def _add_best_candidate_score(
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
    """Return whether two candidates appear to describe the same work.

Args:
    a: First Smeli candidate dictionary.
    b: Second Smeli candidate dictionary.

Returns:
    ``True`` if the candidates share a DOI, arXiv ID, OpenAlex ID, or have a
    strong title/year/author match; otherwise ``False``.
"""
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

    similar_title = _title_similarity(a.get("title"), b.get("title")) >= 0.92
    if not similar_title:
        return False

    # If author lists are present, require some overlap. If one source omitted
    # authors, high title/year similarity is enough.
    authors_a = a.get("authors", [])
    authors_b = b.get("authors", [])
    if authors_a and authors_b:
        return _author_overlap(authors_a, authors_b)

    return True

def merge_candidates(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Merge two candidate dictionaries describing the same work.

Args:
    primary: The preferred candidate record. Existing values are generally kept.
    secondary: A second candidate record used to fill gaps and add sources.

Returns:
    A canonicalized candidate dictionary containing the best available fields
    from both inputs.

Notes:
    This function does not first verify that the records match. Call
    :func:`candidates_are_same` before merging untrusted pairs.
"""
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
        if _title_similarity(merged.get("title"), secondary.get("title")) >= 0.85:
            merged["title"] = secondary["title"]

    if not merged.get("authors") and secondary.get("authors"):
        merged["authors"] = secondary["authors"]
    elif merged.get("authors") and secondary.get("authors"):
        names = list(merged["authors"])
        seen = {_normalize_for_match(name) for name in names}
        for name in secondary["authors"]:
            if _normalize_for_match(name) not in seen:
                names.append(name)
                seen.add(_normalize_for_match(name))
        merged["authors"] = names

    merged["cited_by_count"] = max(
        _maybe_int(merged.get("cited_by_count")) or 0,
        _maybe_int(secondary.get("cited_by_count")) or 0,
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
    """Merge a list of candidate dictionaries across metadata sources.

Args:
    candidates: Candidate records from one or more source APIs.

Returns:
    A list of canonicalized candidate records with likely duplicates collapsed
    using :func:`candidates_are_same` and :func:`merge_candidates`.
"""
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

def bibliographic_query(author: str | None, title: str | None, year: str | int | None) -> str:
    """Build a compact bibliographic query string from available fields.

Args:
    author: Optional author name or fragment.
    title: Optional title or title fragment.
    year: Optional publication year.

Returns:
    A single space-separated query string containing non-empty fields in
    title-author-year order.
"""
    parts = []
    if title:
        parts.append(str(title).strip())
    if author:
        parts.append(str(author).strip())
    if year:
        parts.append(str(year).strip())
    return " ".join(part for part in parts if part)
