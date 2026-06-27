
<div class="smeli-hero title">
  <h1>Smeli</h1>
  <img src="assets/banner.png" alt="Smeli banner">
</div>

<span class="title">**Smeli**</span> is the <span class="title">S</span>cholarly <span class="title">ME</span>tadata <span class="title">L</span>ookup <span class="title">I</span>nterface: a DOI-aware metadata lookup library and command-line tool for scholarly papers.

Smeli can search and normalize metadata from OpenAlex, Crossref, DataCite, arXiv, and doi.org BibTeX content negotiation. DOI is important, but it is not required: DOI-less arXiv and OpenAlex records are valid Smeli candidates.

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
from smeli import get_paper_candidates, candidate_to_bibtex

candidates = get_paper_candidates(query="still building the memex davies")
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

## Some sample DOIs

- _Attention is All you Need_: `10.65215/2q58a426` (DataCite)
- _BERT_: `10.48550/arXiv.1810.04805` (DataCite)
- _Still Building the Memex_: `10.1145/1897816.1897840` (Crossref)
- _XGBoost_: `10.1145/2939672.2939785` (Crossref)

## Some sample ORCIDs

These are useful for trying the author-oriented lookup path:

- Geoffrey Hinton: `0000-0002-8063-7209`
- Jennifer Doudna: `0000-0001-9161-999X`
- Katalin Karikó: `0000-0002-1864-3851`
- Tim Berners-Lee: `0000-0003-1279-3709`

# Questions and feedback

For bug reports, feature requests, or API questions, please open an issue on the
[Smeli GitHub repository](https://github.com/divilian/smeli).

For other questions, contact [Stephen Davies](https://stephendavies.org/).
