# smeli

**smeli** is the Scholarly MEtadata Lookup Interface: a DOI-aware scholarly metadata lookup CLI.

It searches for scholarly work metadata across OpenAlex, Crossref, DataCite, and arXiv. DOI is treated as an important identifier, but not as a gatekeeper: DOI-less arXiv/OpenAlex-style records can still be displayed and converted into BibTeX-like entries.

## Run locally

After installing the project, the console command is:

```bash
smeli
```

## Tests

```bash
pytest
```
