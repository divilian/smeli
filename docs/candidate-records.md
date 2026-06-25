# Candidate Records

A **candidate** is Smeli's normal dictionary representation for a scholarly work. A candidate may describe a journal article, conference paper, arXiv preprint, dataset, software record, repository item, or another scholarly output.

Smeli deliberately uses dictionaries rather than a custom class for now because source APIs vary and the command-line tool benefits from flexible partial records.

## Common keys

| Key | Type | Meaning |
| --- | --- | --- |
| `title` | `str` | Work title, when known. |
| `authors` | `list[str]` | Author display names. |
| `year` | `int | str | None` | Publication year, when known. |
| `venue` | `str` | Journal, conference, arXiv, or container/source name. |
| `publisher` | `str` | Publisher or host organization. |
| `type` | `str` | Source-specific work type. |
| `doi` | `str | None` | Normalized bare DOI, or `None`. |
| `arxiv_id` | `str | None` | Bare arXiv ID without version suffix where possible. |
| `openalex_id` | `str` | OpenAlex work URL/ID when available. |
| `url` | `str` | Best landing URL known to Smeli. |
| `cited_by_count` | `int` | Citation count from the source, usually OpenAlex or Crossref. |
| `metadata_sources` | `list[str]` | Sources that contributed metadata to the merged candidate. |
| `score` | `int` | Smeli's local relevance score for display/ranking. |
| `citation_score` | `int` | Weak citation-count tie-breaker used during ranking. |
| `match_note` | `str` | Optional explanation of a fallback match path. |

## Canonicalization

Call `canonical_candidate()` when you have a partial record and want Smeli's defaults and identifier normalization:

```python
from smeli import canonical_candidate

candidate = canonical_candidate({
    "title": "Example Work",
    "doi": "https://doi.org/10.1234/example",
    "source": "ExampleSource",
})
```

Canonicalization copies the input dictionary, normalizes DOI/arXiv identifiers, fills common optional fields, creates or updates `metadata_sources`, and derives a landing URL when possible.

## Merging

Source APIs often describe the same work slightly differently. Use `merge_candidate_list()` to collapse likely duplicates across source results:

```python
from smeli import merge_candidate_list

merged = merge_candidate_list(crossref_candidates + openalex_candidates)
```

Duplicate detection prefers shared identifiers: DOI, arXiv ID, or OpenAlex ID. When identifiers are missing, Smeli falls back to strong title/year/author similarity.
