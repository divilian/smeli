# smeli

**smeli** is the Scholarly MEtadata Lookup Interface: a DOI-aware scholarly metadata lookup CLI.

It searches for scholarly work metadata across OpenAlex, Crossref, DataCite, and arXiv. DOI is treated as an important identifier, but not as a gatekeeper: DOI-less arXiv/OpenAlex-style records can still be displayed and converted into BibTeX-like entries.

## Run locally

After installing the project, the console command is:

```bash
smeli
```

You can also pass a DOI, arXiv/OpenAlex identifier, or free-form bibliographic text directly on the command line:

```bash
smeli 10.1126/science.1102081
smeli still building the memex davies
```

Identifier lookups go straight to the matching work details when exactly one work is found. Free-form text searches show a ranked candidate list.

## Tests

```bash
pytest
```

## Sample DOIs

- `10.1126/science.1102081`
- `10.1080/03075079.2021.1972093`
- `10.1145/1897816.1897840`
