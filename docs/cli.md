# CLI

The command-line program is installed through the project script entrypoint:

```toml
[project.scripts]
smeli = "smeli.cli:main"
```

Run the interactive menu with:

```bash
smeli
```

Run a one-shot lookup with a DOI, ORCID, arXiv/OpenAlex identifier, or free-form bibliographic query:

```bash
smeli 10.1126/science.1102081
smeli 0000-0002-0254-6627
smeli still building the memex davies
```

`smeli.cli.main()` is public because it is the console-script target. Python package users should usually call functions from `smeli.sources` instead.
