# smeli

**smeli** is the Scholarly MEtadata Lookup Interface: a DOI-aware scholarly metadata lookup CLI.

It searches for scholarly paper metadata across OpenAlex, Crossref, DataCite, and arXiv. DOI is treated as an important identifier, but not as a gatekeeper: DOI-less arXiv/OpenAlex-style records can still be displayed and converted into BibTeX-like entries.

## Run locally

After installing the project, the console command is:

```bash
smeli
```

You can also pass a DOI, ORCID, arXiv/OpenAlex identifier, or free-form bibliographic text directly on the command line:

```bash
smeli 10.1126/science.1102081
smeli 0000-0002-1825-0097
smeli still building the memex davies
```

Identifier and free-form lookups go straight to paper details when exactly one paper is found. ORCID lookups usually return an author's ranked paper list.

## Optional environment variables

Smeli works without private credentials, but you can create a local `.env` file in the project root to identify your requests and enable authenticated OpenAlex requests:

```dotenv
DOI_EMAIL=youremail
OPENALEX_API_KEY=apikey
```

`DOI_EMAIL` is included in Smeli's HTTP `User-Agent` so DOI services have a contact address for polite API use. `OPENALEX_API_KEY` is optional; when present, Smeli includes it on OpenAlex requests.

## API documentation

The public Python API is documented in `docs/` and can be served locally with MkDocs:

```bash
pip install -e '.[docs]'
mkdocs serve
```

The public API surface is defined by each module's `__all__` list.

## Tests

```bash
pytest
```

## Sample DOIs

- _Attention is All you Need_: `10.65215/2q58a426` (DataCite)
- _BERT_: `10.48550/arXiv.1810.04805` (DataCite)
- _Still Building the Memex_: `10.1145/1897816.1897840` (Crossref)
- _XGBoost_: `10.1145/2939672.2939785` (Crossref)

## Sample ORCIDs

These are useful for trying the author-oriented lookup path:

- Geoffrey Hinton: `0000-0002-8063-7209`
- Jennifer Doudna: `0000-0001-9161-999X`
- Katalin Karikó: `0000-0002-1864-3851`
- Tim Berners-Lee: `0000-0003-1279-3709`
