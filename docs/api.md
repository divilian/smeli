# API Overview

Smeli's public API is defined by each module's `__all__` list. Names not included in `__all__` are private implementation details and may change without notice.

The top-level package re-exports the public library API, so this is the normal import style:

```python
from smeli import get_work_candidates, clean_doi, candidate_to_bibtex
```

You can also import from specific modules when that makes the code clearer:

```python
from smeli.sources import get_candidate_from_doi
from smeli.normalize import extract_orcid
```

## Public modules

| Module | Purpose |
| --- | --- |
| `smeli.normalize` | Pure identifier normalization helpers for DOI, ORCID, and arXiv IDs. |
| `smeli.candidates` | Pure local helpers for canonicalizing, scoring, comparing, and merging candidate records. |
| `smeli.sources` | Networked metadata lookups against Crossref, DataCite, OpenAlex, arXiv, and doi.org. |
| `smeli.bibtex` | Small BibTeX parser/printer plus Smeli fallback BibTeX generation. |
| `smeli.cli` | The `main()` console-script entrypoint for the `smeli` command. |

## Recommended entrypoints

Most package users should start with `get_work_candidates()`:

```python
from smeli import get_work_candidates

candidates = get_work_candidates(query="opinion dynamics starnini")
```

Use `get_work_candidates_from_identifier()` when the user supplied a DOI, arXiv ID, OpenAlex work ID, or ORCID:

```python
from smeli import get_work_candidates_from_identifier

works = get_work_candidates_from_identifier("0000-0002-0254-6627")
```

Use `get_candidate_from_doi()`, `get_candidate_from_arxiv_id()`, or `get_candidate_from_openalex_id()` when your code already knows it is resolving a specific work identifier.

## Return conventions

Smeli uses simple Python data structures:

- candidate lookups return `list[dict[str, Any]]`
- single-work lookups return `dict[str, Any] | None`
- metadata lookups return `dict[str, Any] | None`
- ORCID helpers return `list[dict[str, str]]`
- BibTeX lookup returns `str | None`

Expected misses return `None` or `[]`. Real network or parsing problems may also print short diagnostic messages.

## Stability rule

Only names in `__all__` are public. Leading-underscore names are private, even if tests import them internally.
