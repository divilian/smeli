# Examples

## Normalize user-supplied identifiers

```python
from smeli import clean_doi, extract_arxiv_id, extract_orcid

print(clean_doi("https://doi.org/10.1126/science.1102081"))
print(extract_arxiv_id("https://arxiv.org/abs/2501.01234v2"))
print(extract_orcid("https://orcid.org/0000-0002-0254-6627"))
```

## Search by free-form bibliographic query

```python
from smeli import get_work_candidates

candidates = get_work_candidates(query="still building the memex davies")

for candidate in candidates[:5]:
    print(candidate["score"], candidate["title"], candidate.get("doi"))
```

## Search by fielded metadata

```python
from smeli import get_work_candidates

candidates = get_work_candidates(
    title="Still building the memex",
    author="Davies",
    year=2011,
)
```

## Resolve a work identifier

```python
from smeli import get_work_candidates_from_identifier

works = get_work_candidates_from_identifier("10.1126/science.1102081")
```

## Resolve an ORCID

ORCID identifies a person, not a work, so Smeli returns a list of works:

```python
from smeli import get_work_candidates_from_identifier

works = get_work_candidates_from_identifier("0000-0002-0254-6627")
for work in works:
    print(work.get("year"), work.get("title"))
```

## Generate fallback BibTeX

```python
from smeli import candidate_to_bibtex, get_work_candidates

candidates = get_work_candidates(query="still building the memex davies")
if candidates:
    print(candidate_to_bibtex(candidates[0]))
```

When a DOI exists, prefer doi.org BibTeX first:

```python
from smeli import candidate_to_bibtex, get_bibtex_from_doi

bibtex = get_bibtex_from_doi("10.1126/science.1102081")
if bibtex is None:
    bibtex = candidate_to_bibtex(candidate)
```
