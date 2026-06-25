# Development

## Test suite

Smeli's tests are intentionally fast and offline. They use fake or monkeypatched API responses rather than live requests to doi.org, OpenAlex, Crossref, DataCite, or arXiv.

```bash
pytest
```

## Compile check

```bash
python3 -m py_compile smeli/*.py
```

## Documentation dependencies

Install the documentation extras to build or serve the site locally:

```bash
pip install -e '.[docs]'
```

Then run:

```bash
mkdocs serve
```

or build static HTML:

```bash
mkdocs build
```

The static site is written to `site/` and can be hosted with GitHub Pages or any static web host.

## Public API rule

The public API is defined by `__all__`. Every public name should have a useful docstring and a reference page entry. Leading-underscore names are private implementation details.
