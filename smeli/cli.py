"""Command-line interface for smeli."""
from __future__ import annotations

import pydoc
import re
import sys
from pprint import pformat
from typing import Any

from .bibtex import candidate_to_bibtex, print_bibtex
from .candidates import canonical_candidate
from .normalize import clean_doi, extract_arxiv_id, extract_orcid, get_year_from_date
from .config import MAX_DISPLAY_CANDIDATES
from .sources import (
    get_best_structured_metadata,
    get_bibtex_from_doi,
    get_candidate_from_doi,
    get_orcids_from_openalex,
    get_work_candidates,
)


ANSI_RESET = "\033[0m"
TITLE_COLOR = "\033[31m"         # red
AUTHOR_COLOR = "\033[38;5;208m"  # orange
YEAR_COLOR = "\033[34m"          # blue
ID_COLOR = "\033[38;5;205m"      # pink


def color_text(value: Any, color: str) -> str:
    """Return value as ANSI-colored text for terminal display."""
    text = str(value)
    return f"{color}{text}{ANSI_RESET}"


def color_title(value: Any) -> str:
    return color_text(value, TITLE_COLOR)


def color_author(value: Any) -> str:
    return color_text(value, AUTHOR_COLOR)


def color_year(value: Any) -> str:
    return color_text(value, YEAR_COLOR)


def color_identifier(value: Any) -> str:
    return color_text(value, ID_COLOR)


def identifier_type(identifier: str | None) -> str | None:
    """Return a friendly identifier type label for search display."""
    if not identifier:
        return None
    if extract_doi_from_text(identifier):
        return "DOI"
    if extract_orcid(identifier):
        return "ORCID"
    if extract_arxiv_id(identifier):
        return "arXiv"
    if extract_openalex_id_from_text(identifier):
        return "OpenAlex"
    return None


def colored_pformat(key: str, value: Any) -> str:
    """Pretty-format a value, adding Smeli's display colors for key fields."""
    rendered = pformat(value)
    if key == "title":
        return color_title(rendered)
    if key == "authors":
        return color_author(rendered)
    if key == "year":
        return color_year(rendered)
    if key in {"doi", "arxiv_id", "openalex_id"}:
        return color_identifier(rendered)
    return rendered


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
            print(f"title: {color_title(search_data['title'])}")
        if search_data.get("author"):
            print(f"author: {color_author(search_data['author'])}")
        if search_data.get("year"):
            print(f"year: {color_year(search_data['year'])}")
        if search_data.get("identifier"):
            kind = identifier_type(search_data.get("identifier"))
            label = f"identifier ({kind})" if kind else "identifier"
            print(f"{label}: {color_identifier(search_data['identifier'])}")
        if search_data.get("query"):
            print(f"query: {search_data['query']}")

def format_authors(authors: list[str], max_authors: int = 4) -> str:
    """Return a compact author display string."""
    if not authors:
        return ""
    if len(authors) <= max_authors:
        return ", ".join(authors)
    return ", ".join(authors[:max_authors]) + ", et al."

def format_identifier_line(label: str, value: str | None) -> str:
    """Format one identifier line, showing an em dash for missing values."""
    return f"   {label}: {color_identifier(value) if value else '—'}\n"

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

    retval = f"{prefix}{color_title(title)}{score_text}\n"
    retval += f"   {color_author(authors)} ({color_year(year)})\n"
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
        print(f"  {k}: {colored_pformat(k, v)}")

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

def print_selected_work_details(
    candidate: dict[str, Any],
    *,
    pause_at_end: bool = True,
) -> None:
    """Print structured metadata, identifiers, and BibTeX for a selected work."""
    title = candidate.get("title") or candidate.get("doi") or candidate.get("arxiv_id") or "Selected work"
    print("\n" + "=" * 60)
    print(color_title(title))
    print("=" * 60)

    print_selected_work_metadata(candidate)
    input("(Press Enter.)")

    doi = candidate.get("doi")
    used_doi_org_bibtex = False

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
            input("(Press Enter.)")
        else:
            print_bibtex(bibtex)
            used_doi_org_bibtex = True
            if pause_at_end:
                input("(Press Enter to continue.)")
    else:
        print("\n--- DOI-specific enrichment skipped ---")
        print("This selected work does not currently have a DOI in the merged metadata.")
        input("(Press Enter.)")

    if not used_doi_org_bibtex:
        print("\n--- Generated BibTeX-like entry from available metadata ---")
        generated = candidate_to_bibtex(candidate)
        print_bibtex(generated)
        if pause_at_end:
            input("(Press Enter to continue.)")

    print("=" * 60)

def print_selected_doi_details(doi: str) -> None:
    """Print details for a selected DOI."""
    candidate = get_candidate_from_doi(doi) or canonical_candidate({"doi": doi, "source": "user-supplied DOI"})
    print_selected_work_details(candidate)

def extract_doi_from_text(text: str) -> str | None:
    """Extract a DOI from arbitrary command-line text, if one is present."""
    match = re.search(
        r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/\S+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return clean_doi(match.group(1))


def extract_openalex_id_from_text(text: str) -> str | None:
    """Extract an OpenAlex work ID or URL from arbitrary text, if present."""
    match = re.search(r"https?://openalex\.org/(?:works/)?(W\d+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)

    stripped = text.strip()
    if re.fullmatch(r"W\d+", stripped, flags=re.IGNORECASE):
        return stripped

    return None


def remove_first_year(text: str, year: str | None) -> str:
    """Remove one standalone year token from free-form query text."""
    if not year:
        return text.strip()
    return re.sub(r"\s+", " ", re.sub(rf"\b{re.escape(year)}\b", " ", text, count=1)).strip()


def infer_search_data_from_text(text: str) -> dict[str, str | None]:
    """
    Infer a smeli search from arbitrary command-line text.

    Identifiers win because DOI, arXiv, and OpenAlex IDs are intended to name a
    specific work. Otherwise the text is treated as a broad bibliographic query,
    with a standalone four-digit year extracted when present.
    """
    text = text.strip()
    search_data: dict[str, str | None] = {
        "title": None,
        "author": None,
        "year": None,
        "identifier": None,
        "query": None,
    }

    doi = extract_doi_from_text(text)
    if doi:
        search_data["identifier"] = doi
        return search_data

    arxiv_id = extract_arxiv_id(text)
    if arxiv_id:
        search_data["identifier"] = arxiv_id
        return search_data

    orcid = extract_orcid(text)
    if orcid:
        search_data["identifier"] = orcid
        return search_data

    openalex_id = extract_openalex_id_from_text(text)
    if openalex_id:
        search_data["identifier"] = openalex_id
        return search_data

    year = get_year_from_date(text)
    query = remove_first_year(text, str(year) if year else None)
    search_data["year"] = str(year) if year else None
    search_data["query"] = query or text
    return search_data


def print_result_counts(results: list[dict[str, Any]]) -> None:
    """Print a compact count summary for candidate results."""
    doi_count = sum(1 for result in results if result.get("doi"))
    arxiv_count = sum(1 for result in results if result.get("arxiv_id"))
    print(
        f"Found {len(results)} candidate work(s): "
        f"{doi_count} with DOI, {arxiv_count} with arXiv ID."
    )


def choose_from_results(
    results: list[dict[str, Any]],
    *,
    pause_at_end: bool = True,
) -> None:
    """Let the user select a candidate from an already-fetched result list."""
    while True:
        print()
        print_candidates(results)

        work_choice = input(
            "Choose work number (or [q]uit): "
        ).strip().lower()

        if work_choice == "q":
            return

        try:
            idx = int(work_choice) - 1
        except ValueError:
            print("Please enter a valid number or 'q'.")
            continue

        if not (0 <= idx < min(len(results), MAX_DISPLAY_CANDIDATES)):
            print("Invalid number. Please choose from the displayed list.")
            continue

        selected = results[idx]
        print_selected_work_details(selected, pause_at_end=pause_at_end)


def show_lookup_results(
    search_data: dict[str, str | None],
    *,
    direct_identifier: bool = False,
    force_list: bool = False,
    pause_at_end: bool = True,
    show_search_data_on_no_results: bool = True,
) -> bool:
    """Run a search and present either details or a selectable result list.

    Return True when at least one candidate was found, otherwise False.
    """
    print("Looking up work candidates...")
    results = get_work_candidates(**search_data)

    if not results:
        print("No work candidates found matching those criteria.")
        if show_search_data_on_no_results:
            print_search_data(search_data)
        return False

    if not force_list and len(results) == 1:
        if direct_identifier:
            print("Found one work for that identifier.")
        else:
            print("Found one candidate work.")
        print_selected_work_details(results[0], pause_at_end=pause_at_end)
        return True

    print_result_counts(results)
    choose_from_results(results, pause_at_end=pause_at_end)
    return True


def run_one_shot(args: list[str]) -> None:
    """Run a non-menu lookup from command-line arguments."""
    force_list = False
    query_parts: list[str] = []

    for arg in args:
        if arg == "--list":
            force_list = True
        else:
            query_parts.append(arg)

    query_text = " ".join(query_parts).strip()
    if not query_text:
        main([])
        return

    search_data = infer_search_data_from_text(query_text)
    direct_identifier = bool(search_data.get("identifier"))
    show_lookup_results(
        search_data,
        direct_identifier=direct_identifier,
        force_list=force_list,
        pause_at_end=False,
        show_search_data_on_no_results=False,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the scholarly metadata lookup CLI."""
    if argv is None:
        argv = sys.argv[1:]

    if argv:
        run_one_shot(argv)
        return

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
            value = input("identifier (DOI, arXiv, ORCID, or OpenAlex): ").strip()
            search_data = {"title": None, "author": None, "year": None, "identifier": value or None}
            print_search_data(search_data)
            continue

        if choice == "l":
            if not any(search_data.values()):
                print("Please enter a title, author, year, or identifier first.")
                continue

            direct_identifier = bool(search_data.get("identifier"))
            found = show_lookup_results(search_data, direct_identifier=direct_identifier)
            if found and not direct_identifier:
                print_search_data(search_data)
            continue

        print("Invalid option. Please try again.")
