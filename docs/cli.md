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

Show command-line usage with:

```bash
smeli -h
# or
smeli --help
```

Run a one-shot lookup with a DOI, ORCID, arXiv/OpenAlex identifier, or free-form bibliographic query:

```bash
smeli 10.1126/science.1102081
smeli 0000-0002-0254-6627
smeli still building the memex davies
```

You can also provide fielded search terms directly from the shell:

```bash
smeli --author "Stephen Davies" --title "Still building the memex" --year 1995
smeli -a "Starnini" -t "opinion dynamics"
smeli --identifier 10.1126/science.1102081
```

Use `--list` with either style to force a selectable result list even when Smeli finds a single match:

```bash
smeli --list --author "Stephen Davies" --title "Still building the memex"
```

## Importing BibTeX into Zotero

When Smeli displays a BibTeX entry, Zotero can create a new library item directly from it:

1. Copy the complete BibTeX entry to the clipboard.
2. In Zotero, choose **File → Import from Clipboard**.
3. Zotero parses the BibTeX metadata and creates the new item in the currently selected library or collection.

`smeli.cli.main()` is public because it is the console-script target. Python package users should usually call functions from `smeli.sources` instead.
