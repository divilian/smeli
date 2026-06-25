# API Overview

Smeli's public API is defined by each module's `__all__` list. Names not included in `__all__` are private implementation details and may change without notice.

The top-level package re-exports the public library API, so this is the normal import style:

```python
from smeli import get_paper_candidates, search_orcids, candidate_to_bibtex
```

You can also import from specific modules when that makes the code clearer:

```python
from smeli.sources import get_candidate_from_doi
from smeli.normalize import extract_orcid
```

## Public modules

| Module | Purpose |
| --- | --- |
| [`smeli.normalize`](reference/normalize.md) | Pure identifier normalization helpers for DOI, ORCID, and arXiv IDs. |
| [`smeli.candidates`](reference/candidates.md) | Pure local helpers for canonicalizing, scoring, comparing, and merging candidate records. |
| [`smeli.sources`](reference/sources.md) | Networked metadata lookups against Crossref, DataCite, OpenAlex, arXiv, and doi.org. |
| [`smeli.bibtex`](reference/bibtex.md) | Small BibTeX parser/printer plus Smeli fallback BibTeX generation. |
| [`smeli.cli`](reference/cli.md) | The `main()` console-script entrypoint for the `smeli` command. |

## Recommended entrypoints

Most package users should start with `get_paper_candidates()`:

```python
from smeli import get_paper_candidates

candidates = get_paper_candidates(query="opinion dynamics starnini")
```

Use `get_paper_candidates_from_identifier()` when the user supplied a DOI, arXiv ID, OpenAlex Work ID, or ORCID:

```python
from smeli import get_paper_candidates_from_identifier

papers = get_paper_candidates_from_identifier("0000-0002-0254-6627")
```

Use `get_candidate_from_doi()`, `get_candidate_from_arxiv_id()`, or `get_candidate_from_openalex_id()` when your code already knows it is resolving a specific paper identifier. Use `search_orcids()` when you have an author name fragment and want possible author/ORCID matches.

## Return conventions

Smeli uses simple Python data structures:

- candidate lookups return `list[dict[str, Any]]`
- single-paper lookups return `dict[str, Any] | None`
- metadata lookups return `dict[str, Any] | None`
- `get_orcids()` returns `list[str]`
- source-specific ORCID helpers and `search_orcids()` return `list[dict[str, Any]]`
- BibTeX lookup returns `str | None`

Expected misses return `None` or `[]`. Real network or parsing problems may also print short diagnostic messages.

## Stability rule

Only names in `__all__` are public. Leading-underscore names are private, even if tests import them internally.
