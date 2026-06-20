#!/usr/bin/env python3
"""
doi.py

A small CLI helper for finding DOIs and fetching metadata for selected DOIs.

Search/discovery is primarily done through OpenAlex. Once a DOI is selected,
the script tries:

  - Crossref for structured metadata, when the DOI has a Crossref record
  - OpenAlex for author ORCIDs
  - doi.org content negotiation for BibTeX

Some functions are not currently used by the CLI, but are kept around as
useful experiments / future building blocks.
"""

import os
import re
import sys
import unicodedata
from dotenv import load_dotenv
from pprint import pprint
from typing import Any
from urllib.parse import quote

import pydoc
import requests

load_dotenv()

# ---------------------------------------------------------
# Request helpers
# ---------------------------------------------------------

DEFAULT_TIMEOUT = 20

# Crossref recommends identifying scripts that use its API. Keeping the email
# configurable makes the script easier to share later.
#
# DOI_EMAIL is the preferred setting name for this script. DOI_PLAY_EMAIL is
# accepted as an older/backward-compatible name.
CONTACT_EMAIL = os.getenv("DOI_EMAIL") or os.getenv("DOI_PLAY_EMAIL", "")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")

if CONTACT_EMAIL:
    USER_AGENT = f"doi/0.1 (mailto:{CONTACT_EMAIL})"
else:
    USER_AGENT = "doi/0.1"

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
            return doi[len(prefix):].strip()

    return doi


def quote_doi_for_path(doi: str) -> str:
    """
    Quote a DOI for APIs that place the DOI inside a URL path segment.

    The slash between the DOI prefix and suffix must be encoded for APIs like
    Crossref and OpenAlex path lookups.
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
    """Normalize text for forgiving-but-still-simple substring matching."""
    if not text:
        return ""

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


def get_year_from_crossref(data: dict[str, Any]) -> int | None:
    """Extract the best available publication year from Crossref metadata."""
    for field in ("published-print", "published-online", "published", "issued"):
        date_parts = data.get(field, {}).get("date-parts")
        if date_parts and date_parts[0]:
            return date_parts[0][0]
    return None


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


def crossref_item_to_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a Crossref result item into a candidate result dictionary."""
    doi = clean_doi(item.get("DOI"))
    if not doi:
        return None

    return {
        "doi": doi,
        "title": first(item.get("title"), ""),
        "year": get_year_from_crossref(item),
        "authors": author_names_from_crossref(item),
        "venue": first(item.get("container-title"), ""),
        "publisher": item.get("publisher", ""),
        "cited_by_count": item.get("is-referenced-by-count", 0),
        "source": "Crossref",
        "id": item.get("URL", ""),
    }


def openalex_item_to_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert an OpenAlex work item into a candidate result dictionary."""
    doi = clean_doi(item.get("doi"))
    if not doi:
        # This CLI is about DOI lookup, so suppress no-DOI OpenAlex works.
        return None

    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}

    return {
        "doi": doi,
        "title": item.get("title", "") or "",
        "year": item.get("publication_year"),
        "authors": author_names_from_openalex(item),
        "venue": source.get("display_name", "") or "",
        "publisher": source.get("host_organization_name", "") or "",
        "cited_by_count": item.get("cited_by_count", 0),
        "source": "OpenAlex",
        "id": item.get("id", ""),
    }


def candidate_matches(
    candidate: dict[str, Any],
    *,
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> bool:
    """Apply local strict-ish matching to a structured candidate."""
    if title and not contains_normalized(candidate.get("title"), title):
        return False

    if author:
        authors = candidate.get("authors", [])
        if not any(contains_normalized(name, author) for name in authors):
            return False

    if year:
        if str(candidate.get("year")) != str(year).strip():
            return False

    return True


def candidate_score(
    candidate: dict[str, Any],
    *,
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> tuple[int, int]:
    """
    Return a simple ranking score for a DOI candidate.

    The score is only used after candidate_matches() has already decided that a
    result is plausible. In other words: matching decides whether to include a
    candidate; scoring decides which plausible candidates should be shown first.
    """
    score = 0

    candidate_title = normalize_for_match(candidate.get("title"))
    query_title = normalize_for_match(title)

    if query_title:
        if candidate_title == query_title:
            score += 100
        elif candidate_title.startswith(query_title):
            score += 80
        elif query_title in candidate_title:
            score += 60

        # Prefer tight title matches over much longer titles that merely
        # contain the query as a substring.
        title_word_gap = abs(
            len(candidate_title.split()) - len(query_title.split())
        )
        score -= min(title_word_gap, 20)

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
        # signal, especially for quick scholarly DOI lookup.
        if candidate_authors and query_author in candidate_authors[0]:
            score += 10

    if year and str(candidate.get("year")) == str(year).strip():
        score += 30

    if candidate.get("doi"):
        score += 10

    # Very weak tie-breaker. Citation count should not overpower title,
    # author, or year matching.
    try:
        citations = int(candidate.get("cited_by_count") or 0)
    except (TypeError, ValueError):
        citations = 0
    citation_bonus = min(citations, 1000)

    return score, citation_bonus


def get_doi_from_crossref(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch DOI candidates from Crossref matching the provided criteria.

    This function is currently unused by the CLI, which uses OpenAlex for
    discovery, but it is kept as an alternate search path.
    """
    url = "https://api.crossref.org/works"

    params: dict[str, Any] = {"rows": 50}
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
        if candidate_matches(candidate, author=author, title=title, year=year):
            matched.append(candidate)

    matched.sort(
        key=lambda c: candidate_score(c, author=author, title=title, year=year),
        reverse=True,
    )
    return matched


def get_doi_from_openalex(
    author: str | None = None,
    title: str | None = None,
    year: str | int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch DOI candidates from OpenAlex matching the provided criteria.

    We send the most useful available search text to OpenAlex, then do local
    normalized matching on title, author, and year. This avoids the earlier
    problem where author-only searches accidentally searched the global top 100
    works rather than works related to that author.
    """
    url = "https://api.openalex.org/works"

    params: dict[str, Any] = {
        "per-page": 100,
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
    seen_dois = set()

    for item in items:
        candidate = openalex_item_to_candidate(item)
        if not candidate:
            continue
        if not candidate_matches(candidate, author=author, title=title, year=year):
            continue

        doi_key = candidate["doi"].casefold()
        if doi_key in seen_dois:
            continue
        seen_dois.add(doi_key)
        matched.append(candidate)

    matched.sort(
        key=lambda c: candidate_score(c, author=author, title=title, year=year),
        reverse=True,
    )
    return matched


# ---------------------------------------------------------
# CLI formatting helpers
# ---------------------------------------------------------


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


def format_authors(authors: list[str], max_authors: int = 4) -> str:
    """Return a compact author display string."""
    if not authors:
        return ""
    if len(authors) <= max_authors:
        return ", ".join(authors)
    return ", ".join(authors[:max_authors]) + ", et al."


def serialize_candidate(
    candidate: dict[str, Any],
    index: int | None = None,
) -> str:
    """Return one structured DOI candidate."""
    prefix = f"{index}. " if index is not None else ""
    title = candidate.get("title") or "[No title]"
    year = candidate.get("year") or "n.d."
    authors = format_authors(candidate.get("authors", [])) or "[No authors listed]"
    venue = candidate.get("venue") or candidate.get("publisher") or "[No venue listed]"
    citations = candidate.get("cited_by_count")

    retval = f"{prefix}{title}\n"
    retval += f"   {authors} ({year})\n"
    retval += f"   {venue}\n"
    if citations is not None:
        retval += f"   citations: {citations}\n"
    if candidate.get("source"):
        retval += f"   source: {candidate.get('source')}\n"
    retval += f"   DOI: {candidate.get('doi')}\n"
    return retval

def print_candidates(candidates: list[dict[str, Any]]) -> None:
    """Print numbered DOI candidates."""
    output = ""
    for i, candidate in enumerate(candidates, 1):
        output += serialize_candidate(candidate, i) + "\n"
    page_text(output)

def print_selected_doi_details(doi: str) -> None:
    """Print Crossref metadata, ORCIDs, and BibTeX for a selected DOI."""
    print("\n" + "=" * 60)
    print(f"SELECTED DOI: {doi}")
    print("=" * 60)

    print("\n--- Crossref metadata ---")
    metadata = get_metadata_from_crossref(doi)
    if metadata is None:
        print(
            "No Crossref metadata found. This may still be a valid DOI; "
            "it may simply be registered outside Crossref."
        )
    else:
        pprint(metadata)
    input("(Press Enter.)")

    print("\n--- ORCIDs from OpenAlex ---")
    orcids = get_orcids_from_openalex(doi)
    if not orcids:
        print("[]")
    else:
        pprint(orcids)
    input("(Press Enter.)")

    print("\n--- BibTeX from doi.org ---")
    bibtex = get_bibtex_from_doi(doi)
    if bibtex is None:
        print("No BibTeX returned by doi.org content negotiation.")
    else:
        print(bibtex.strip())
    input("(Press Enter.)")

    print("=" * 60)


# ---------------------------------------------------------
# CLI Main Loop
# ---------------------------------------------------------

def page_text(text: str) -> None:
    """Display long text through the user's pager."""
    pydoc.pager(text)

def main() -> None:
    """Run the DOI lookup CLI."""
    print("Welcome to the DOI lookup program!")

    search_data: dict[str, str | None] = {
        "title": None,
        "author": None,
        "year": None,
    }

    while True:
        prompt = (
            "\nEnter [t]itle, [a]uthor, [y]ear, "
            "[l]ookup, [c]lear, or [q]uit: "
        )
        choice = input(prompt).strip().lower()

        if choice == "q":
            sys.exit(0)

        if choice == "c":
            search_data = {"title": None, "author": None, "year": None}
            print_search_data(search_data)
            continue

        if choice == "t":
            value = input("title: ").strip()
            search_data["title"] = value or None
            print_search_data(search_data)
            continue

        if choice == "a":
            value = input("author: ").strip()
            search_data["author"] = value or None
            print_search_data(search_data)
            continue

        if choice == "y":
            value = input("year: ").strip()
            search_data["year"] = value or None
            print_search_data(search_data)
            continue

        if choice == "l":
            print("Looking up DOI candidates via OpenAlex...")
            results = get_doi_from_openalex(**search_data)

            if not results:
                print("No DOIs found matching those criteria.")
                print_search_data(search_data)
                continue

            # Inner DOI-selection loop
            while True:
                print()
                print_candidates(results)

                doi_choice = input(
                    "Choose DOI number (or [q]uit): "
                ).strip().lower()

                if doi_choice == "q":
                    print_search_data(search_data)
                    break

                try:
                    idx = int(doi_choice) - 1
                except ValueError:
                    print("Please enter a valid number or 'q'.")
                    continue

                if not (0 <= idx < len(results)):
                    print("Invalid number. Please choose from the list.")
                    continue

                selected = results[idx]
                selected_doi = selected.get("doi")
                if not selected_doi:
                    print("That result does not have a DOI.")
                    continue

                print_selected_doi_details(selected_doi)

            continue

        print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
