# Smeli

**Smeli** is the Scholarly MEtadata Lookup Interface: a DOI-aware metadata lookup library and command-line tool for scholarly works.

Smeli can search and normalize metadata from OpenAlex, Crossref, DataCite, arXiv, and doi.org BibTeX content negotiation. DOI is important, but it is not required: DOI-less arXiv and OpenAlex works are valid Smeli candidates.

## Two ways to use Smeli

Use the command-line program when you want an interactive lookup tool:

```bash
smeli
smeli 10.1126/science.1102081
smeli still building the memex davies
smeli 0000-0002-0254-6627
```

Use the Python API when another program wants candidate records, identifier normalization, metadata lookups, or BibTeX generation:

```python
from smeli import get_work_candidates, candidate_to_bibtex

candidates = get_work_candidates(query="still building the memex davies")
for candidate in candidates:
    print(candidate["title"], candidate.get("doi"))

if candidates:
    print(candidate_to_bibtex(candidates[0]))
```

## Start here

- [API Overview](api.md) explains the public API modules and recommended entrypoints.
- [Candidate Records](candidate-records.md) documents the dictionary shape used throughout Smeli.
- [Examples](examples.md) shows common library calls.
- [Reference](reference/smeli.md) contains generated API reference pages from the public docstrings.
