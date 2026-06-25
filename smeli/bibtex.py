"""BibTeX parsing, pretty-printing, and generation.

Smeli prefers doi.org-provided BibTeX when it is available for a DOI. These
helpers support parsing and displaying that BibTeX, and generating a
conservative fallback BibTeX-like entry from Smeli candidate metadata.
"""
from __future__ import annotations

__all__ = [
    "parse_bibtex_entry",
    "print_bibtex",
    "make_cite_key",
    "candidate_to_bibtex",
]


import html
import re
from typing import Any

from .normalize import _author_lastish_name, _normalize_for_match


def _split_bibtex_fields(body: str) -> list[str]:
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

def _clean_bibtex_value(value: str) -> str:
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
    """Parse a single BibTeX entry into a simple dictionary.

    Args:
        bibtex: Text containing one BibTeX entry.

    Returns:
        A dictionary with ``entry_type``, ``cite_key``, and ``fields`` keys, or
        ``None`` if the text does not look like a normal single BibTeX entry.

    Notes:
        This parser is intentionally small. It handles ordinary BibTeX returned
        by DOI content negotiation, but it is not a full BibTeX parser.
    """
    text = bibtex.strip()

    match = re.match(r"@(\w+)\s*\{\s*([^,]+)\s*,(.*)\}\s*$", text, re.DOTALL)
    if not match:
        return None

    entry_type = match.group(1).strip()
    cite_key = match.group(2).strip()
    body = match.group(3).strip()

    fields: dict[str, str] = {}

    for field_text in _split_bibtex_fields(body):
        if "=" not in field_text:
            continue

        key, value = field_text.split("=", 1)
        key = key.strip().lower()
        fields[key] = _clean_bibtex_value(value)

    return {
        "entry_type": entry_type,
        "cite_key": cite_key,
        "fields": fields,
    }

def print_bibtex(bibtex: str) -> None:
    """Print a BibTeX entry in a friendlier field-by-field format.

    Args:
        bibtex: Text containing one BibTeX entry.

    Returns:
        ``None``. Output is written to standard output.

    Notes:
        The raw BibTeX is printed after the field-by-field display so it can
        still be copied into BibTeX-aware tools.
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

def _bibtex_escape(value: Any) -> str:
    """Very small BibTeX escaping/tidying helper."""
    text = str(value or "")
    text = html.unescape(text)
    text = text.replace("{", "\\{").replace("}", "\\}")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def make_cite_key(candidate: dict[str, Any]) -> str:
    """Create a compact citation key from first-author surname and year.

Args:
    candidate: A Smeli candidate dictionary.

Returns:
    A lower-case key in Kurrent/Smeli style, such as ``"davies2011"`` or
    ``"starnini2025"``. Missing authors fall back to ``"work"`` and missing
    years fall back to ``"nd"``.
"""
    authors = candidate.get("authors") or []
    if authors:
        author_part = _author_lastish_name(authors[0]) or "work"
    else:
        author_part = "work"

    year = candidate.get("year") or "nd"
    key = f"{author_part}{year}".lower()
    return re.sub(r"[^a-z0-9_:-]", "", key)

def candidate_to_bibtex(candidate: dict[str, Any]) -> str:
    """Generate a conservative BibTeX-like entry from candidate metadata.

Args:
    candidate: A Smeli candidate dictionary.

Returns:
    A BibTeX-like string using available fields such as title, authors, year,
    venue, DOI, arXiv ID, and URL.

Notes:
    This is a fallback formatter, not a replacement for publisher- or
    resolver-provided BibTeX. Prefer :func:`smeli.sources.get_bibtex_from_doi`
    when a DOI is available and doi.org content negotiation succeeds.
"""
    entry_type = "article"
    if candidate.get("arxiv_id") and not candidate.get("doi"):
        entry_type = "misc"
    elif candidate.get("type") in {"book", "monograph"}:
        entry_type = "book"
    elif candidate.get("venue") and "proceed" in _normalize_for_match(candidate.get("venue")):
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
        lines.append(f"  {key} = {{{_bibtex_escape(value)}}},")
    lines.append("}")
    return "\n".join(lines)
