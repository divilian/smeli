"""Command-line interface for Smeli.

The library-facing public API of this module is intentionally tiny:
`main()` is the console-script entrypoint used by the ``smeli`` command.
Display helpers, prompts, color constants, and one-shot argument handling are
private implementation details.
"""
from __future__ import annotations

__all__ = [
    "main",
]


import pydoc
import re
import sys
from pprint import pformat
from typing import Any

from .bibtex import candidate_to_bibtex, print_bibtex
from .candidates import canonical_candidate
from .normalize import clean_doi, extract_arxiv_id, extract_orcid, _get_year_from_date
from .config import _MAX_DISPLAY_CANDIDATES
from .sources import (
    get_metadata,
    get_bibtex_from_doi,
    get_candidate_from_doi,
    get_orcids,
    get_paper_candidates,
)


_ANSI_RESET = "\033[0m"
_TITLE_COLOR = "\033[31m"         # red
_AUTHOR_COLOR = "\033[38;5;208m"  # orange
_YEAR_COLOR = "\033[34m"          # blue
_ID_COLOR = "\033[38;5;205m"      # pink


def _color_text(value: Any, color: str) -> str:
    """Return value as ANSI-colored text for terminal display."""
    text = str(value)
    return f"{color}{text}{_ANSI_RESET}"


def _color_title(value: Any) -> str:
    return _color_text(value, _TITLE_COLOR)


def _color_author(value: Any) -> str:
    return _color_text(value, _AUTHOR_COLOR)


def _color_year(value: Any) -> str:
    return _color_text(value, _YEAR_COLOR)


def _color_identifier(value: Any) -> str:
    return _color_text(value, _ID_COLOR)


def _identifier_type(identifier: str | None) -> str | None:
    """Return a friendly identifier type label for search display."""
    if not identifier:
        return None
    if _extract_doi_from_text(identifier):
        return "DOI"
    if extract_orcid(identifier):
        return "ORCID"
    if extract_arxiv_id(identifier):
        return "arXiv"
    if _extract_openalex_id_from_text(identifier):
        return "OpenAlex"
    return None


def _colored_pformat(key: str, value: Any) -> str:
    """Pretty-format a value, adding Smeli's display colors for key fields."""
    rendered = pformat(value)
    if key == "title":
        return _color_title(rendered)
    if key == "authors":
        return _color_author(rendered)
    if key == "year":
        return _color_year(rendered)
    if key in {"doi", "arxiv_id", "openalex_id"}:
        return _color_identifier(rendered)
    return rendered


def _page_text(text: str) -> None:
    """Display long text through the user's pager."""
    pydoc.pager(text)

def _print_search_data(search_data: dict[str, str | None]) -> None:
    """Cleanly format the current search criteria."""
    print("\nSearch data so far:")
    if not any(search_data.values()):
        print("(none)")
    else:
        if search_data.get("title"):
            print(f"title: {_color_title(search_data['title'])}")
        if search_data.get("author"):
            print(f"author: {_color_author(search_data['author'])}")
        if search_data.get("year"):
            print(f"year: {_color_year(search_data['year'])}")
        if search_data.get("identifier"):
            kind = _identifier_type(search_data.get("identifier"))
            label = f"identifier ({kind})" if kind else "identifier"
            print(f"{label}: {_color_identifier(search_data['identifier'])}")
        if search_data.get("query"):
            print(f"query: {search_data['query']}")

def _format_authors(authors: list[str], max_authors: int = 4) -> str:
    """Return a compact author display string."""
    if not authors:
        return ""
    if len(authors) <= max_authors:
        return ", ".join(authors)
    return ", ".join(authors[:max_authors]) + ", et al."

def _format_identifier_line(label: str, value: str | None) -> str:
    """Format one identifier line, showing an em dash for missing values."""
    return f"   {label}: {_color_identifier(value) if value else '—'}\n"

def _serialize_candidate(
    candidate: dict[str, Any],
    index: int | None = None,
) -> str:
    """Return one structured paper candidate."""
    prefix = f"{index}. " if index is not None else ""
    title = candidate.get("title") or "[No title]"
    year = candidate.get("year") or "n.d."
    authors = _format_authors(candidate.get("authors", [])) or "[No authors listed]"
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

    retval = f"{prefix}{_color_title(title)}{score_text}\n"
    retval += f"   {_color_author(authors)} ({_color_year(year)})\n"
    retval += f"   {venue}\n"
    if citations is not None:
        retval += f"   citations: {citations}\n"
    if candidate.get("match_note"):
        retval += f"   match note: {candidate.get('match_note')}\n"
    retval += f"   metadata sources: {source_text}\n"
    retval += _format_identifier_line("DOI", candidate.get("doi"))
    retval += _format_identifier_line("arXiv", candidate.get("arxiv_id"))
    retval += _format_identifier_line("OpenAlex", candidate.get("openalex_id"))
    if candidate.get("url"):
        retval += f"   URL: {candidate.get('url')}\n"
    return retval

def _print_candidates(candidates: list[dict[str, Any]]) -> None:
    """Print numbered paper candidates."""
    output = ""
    for i, candidate in enumerate(candidates[:_MAX_DISPLAY_CANDIDATES], 1):
        output += _serialize_candidate(candidate, i) + "\n"

    if len(candidates) > _MAX_DISPLAY_CANDIDATES:
        output += f"... {len(candidates) - _MAX_DISPLAY_CANDIDATES} more candidate(s) not shown.\n"

    _page_text(output)

def _print_dict(d: dict[str, Any]) -> None:
    for k, v in d.items():
        print(f"  {k}: {_colored_pformat(k, v)}")

def _print_list_of_dicts(ld: list[dict[str, Any]]) -> None:
    for i in ld:
        _print_dict(i)
        print()

def _print_selected_paper_metadata(candidate: dict[str, Any]) -> None:
    """Print the metadata already present on a selected candidate."""
    print("\n--- Candidate metadata ---")
    _print_dict({
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

def _print_selected_paper_details(
    candidate: dict[str, Any],
    *,
    pause_at_end: bool = True,
) -> None:
    """Print structured metadata, identifiers, and BibTeX for a selected paper."""
    title = candidate.get("title") or candidate.get("doi") or candidate.get("arxiv_id") or "Selected paper"
    print("\n" + "=" * 60)
    print(_color_title(title))
    print("=" * 60)

    _print_selected_paper_metadata(candidate)
    input("(Press Enter.)")

    doi = candidate.get("doi")
    used_doi_org_bibtex = False

    if doi:
        print("\n--- Structured DOI metadata ---")
        metadata = get_metadata(doi)
        if metadata is None:
            print(
                "No Crossref or DataCite metadata found. This may still be a "
                "valid DOI; it may simply be registered somewhere else or have "
                "limited public metadata."
            )
        else:
            _print_dict(metadata)
        input("(Press Enter.)")

        print("\n--- ORCIDs from metadata sources ---")
        orcids = get_orcids(doi)
        if not orcids:
            print("[]")
        else:
            for orcid in orcids:
                print(f"  - {orcid}")
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
        print("This selected paper does not currently have a DOI in the merged metadata.")
        input("(Press Enter.)")

    if not used_doi_org_bibtex:
        print("\n--- Generated BibTeX-like entry from available metadata ---")
        generated = candidate_to_bibtex(candidate)
        print_bibtex(generated)
        if pause_at_end:
            input("(Press Enter to continue.)")

    print("=" * 60)

def _print_selected_doi_details(doi: str) -> None:
    """Print details for a selected DOI."""
    candidate = get_candidate_from_doi(doi) or canonical_candidate({"doi": doi, "source": "user-supplied DOI"})
    _print_selected_paper_details(candidate)

def _extract_doi_from_text(text: str) -> str | None:
    """Extract a DOI from arbitrary command-line text, if one is present."""
    match = re.search(
        r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/\S+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return clean_doi(match.group(1))


def _extract_openalex_id_from_text(text: str) -> str | None:
    """Extract an OpenAlex Work ID or URL from arbitrary text, if present."""
    match = re.search(r"https?://openalex\.org/(?:works/)?(W\d+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)

    stripped = text.strip()
    if re.fullmatch(r"W\d+", stripped, flags=re.IGNORECASE):
        return stripped

    return None


def _remove_first_year(text: str, year: str | None) -> str:
    """Remove one standalone year token from free-form query text."""
    if not year:
        return text.strip()
    return re.sub(r"\s+", " ", re.sub(rf"\b{re.escape(year)}\b", " ", text, count=1)).strip()


def _infer_search_data_from_text(text: str) -> dict[str, str | None]:
    """
    Infer a smeli search from arbitrary command-line text.

    Identifiers win because DOI, arXiv, and OpenAlex IDs are intended to name a
    specific paper. Otherwise the text is treated as a broad bibliographic query,
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

    doi = _extract_doi_from_text(text)
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

    openalex_id = _extract_openalex_id_from_text(text)
    if openalex_id:
        search_data["identifier"] = openalex_id
        return search_data

    year = _get_year_from_date(text)
    query = _remove_first_year(text, str(year) if year else None)
    search_data["year"] = str(year) if year else None
    search_data["query"] = query or text
    return search_data


def _print_result_counts(results: list[dict[str, Any]]) -> None:
    """Print a compact count summary for candidate results."""
    doi_count = sum(1 for result in results if result.get("doi"))
    arxiv_count = sum(1 for result in results if result.get("arxiv_id"))
    print(
        f"Found {len(results)} candidate paper(s): "
        f"{doi_count} with DOI, {arxiv_count} with arXiv ID."
    )


def _choose_from_results(
    results: list[dict[str, Any]],
    *,
    pause_at_end: bool = True,
) -> None:
    """Let the user select a candidate from an already-fetched result list."""
    while True:
        print()
        _print_candidates(results)

        paper_choice = input(
            "Choose paper number (or [q]uit): "
        ).strip().lower()

        if paper_choice == "q":
            return

        try:
            idx = int(paper_choice) - 1
        except ValueError:
            print("Please enter a valid number or 'q'.")
            continue

        if not (0 <= idx < min(len(results), _MAX_DISPLAY_CANDIDATES)):
            print("Invalid number. Please choose from the displayed list.")
            continue

        selected = results[idx]
        _print_selected_paper_details(selected, pause_at_end=pause_at_end)


def _show_lookup_results(
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
    print("Looking up paper candidates...")
    results = get_paper_candidates(**search_data, progress=print)

    if not results:
        print("No paper candidates found matching those criteria.")
        if show_search_data_on_no_results:
            _print_search_data(search_data)
        return False

    if not force_list and len(results) == 1:
        if direct_identifier:
            print("Found one paper for that identifier.")
        else:
            print("Found one candidate paper.")
        _print_selected_paper_details(results[0], pause_at_end=pause_at_end)
        return True

    _print_result_counts(results)
    _choose_from_results(results, pause_at_end=pause_at_end)
    return True


def _run_one_shot(args: list[str]) -> None:
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

    search_data = _infer_search_data_from_text(query_text)
    direct_identifier = bool(search_data.get("identifier"))
    _show_lookup_results(
        search_data,
        direct_identifier=direct_identifier,
        force_list=force_list,
        pause_at_end=False,
        show_search_data_on_no_results=False,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the scholarly metadata lookup CLI.

Args:
    argv: Optional command-line arguments excluding the program name. When
        ``None``, arguments are read from ``sys.argv``.

Returns:
    None: Results are printed to standard output and interactive prompts read
        from standard input.

Notes:
    Normal package users should prefer the lookup functions in
    :mod:`smeli.sources`. This function is public primarily because it is the
    console-script target for the ``smeli`` command.
"""
    if argv is None:
        argv = sys.argv[1:]

    if argv:
        _run_one_shot(argv)
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
            _print_search_data(search_data)
            continue

        if choice == "t":
            value = input("title: ").strip()
            search_data["title"] = value or None
            search_data["identifier"] = None
            _print_search_data(search_data)
            continue

        if choice == "a":
            value = input("author: ").strip()
            search_data["author"] = value or None
            search_data["identifier"] = None
            _print_search_data(search_data)
            continue

        if choice == "y":
            value = input("year: ").strip()
            search_data["year"] = value or None
            search_data["identifier"] = None
            _print_search_data(search_data)
            continue

        if choice == "i":
            value = input("identifier (DOI, arXiv, ORCID, or OpenAlex): ").strip()
            search_data = {"title": None, "author": None, "year": None, "identifier": value or None}
            _print_search_data(search_data)
            continue

        if choice == "l":
            if not any(search_data.values()):
                print("Please enter a title, author, year, or identifier first.")
                continue

            direct_identifier = bool(search_data.get("identifier"))
            found = _show_lookup_results(search_data, direct_identifier=direct_identifier)
            if found and not direct_identifier:
                _print_search_data(search_data)
            continue

        print("Invalid option. Please try again.")
