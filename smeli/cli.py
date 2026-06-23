"""Command-line interface for smeli."""
from __future__ import annotations

import pydoc
import sys
from pprint import pformat
from typing import Any

from .bibtex import candidate_to_bibtex, print_bibtex
from .candidates import canonical_candidate
from .config import MAX_DISPLAY_CANDIDATES
from .sources import (
    get_best_structured_metadata,
    get_bibtex_from_doi,
    get_candidate_from_doi,
    get_orcids_from_openalex,
    get_work_candidates,
)


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

def print_selected_doi_details(doi: str) -> None:
    """Print details for a selected DOI."""
    candidate = get_candidate_from_doi(doi) or canonical_candidate({"doi": doi, "source": "user-supplied DOI"})
    print_selected_work_details(candidate)

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
