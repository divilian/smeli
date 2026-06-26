import builtins

import smeli.cli as cli


def test_doi_work_uses_doi_org_bibtex_without_generated_fallback(monkeypatch, capsys):
    candidate = {
        "title": "Still building the memex",
        "authors": ["Stephen Davies"],
        "year": 2011,
        "venue": "Communications of the ACM",
        "doi": "10.1145/1897816.1897840",
    }

    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    monkeypatch.setattr(cli, "get_metadata", lambda doi: {"source": "Crossref", "doi": doi})
    monkeypatch.setattr(cli, "get_orcids", lambda doi: [])
    monkeypatch.setattr(
        cli,
        "get_bibtex_from_doi",
        lambda doi: "@article{Davies_2011, title = {Still building the memex}, year = {2011}}",
    )

    cli._print_selected_paper_details(candidate, pause_at_end=False)

    output = capsys.readouterr().out
    assert "--- BibTeX from doi.org ---" in output
    assert "citation key: Davies_2011" in output
    assert "Raw BibTeX:" in output
    assert "Generated BibTeX-like entry" not in output
    assert output.count("Raw BibTeX:") == 1


def test_doi_work_generates_bibtex_when_doi_org_has_no_bibtex(monkeypatch, capsys):
    candidate = {
        "title": "Still building the memex",
        "authors": ["Stephen Davies"],
        "year": 2011,
        "venue": "Communications of the ACM",
        "doi": "10.1145/1897816.1897840",
    }

    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    monkeypatch.setattr(cli, "get_metadata", lambda doi: {"source": "Crossref", "doi": doi})
    monkeypatch.setattr(cli, "get_orcids", lambda doi: [])
    monkeypatch.setattr(cli, "get_bibtex_from_doi", lambda doi: None)

    cli._print_selected_paper_details(candidate, pause_at_end=False)

    output = capsys.readouterr().out
    assert "No BibTeX returned by doi.org content negotiation." in output
    assert "--- Generated BibTeX-like entry from available metadata ---" in output
    assert "citation key: davies2011" in output


def test_doi_less_work_prints_generated_bibtex(monkeypatch, capsys):
    candidate = {
        "title": "Opinion dynamics: Statistical physics and beyond",
        "authors": ["Michele Starnini"],
        "year": 2025,
        "venue": "arXiv",
        "arxiv_id": "2507.11521",
        "doi": None,
    }

    monkeypatch.setattr(builtins, "input", lambda prompt="": "")

    cli._print_selected_paper_details(candidate, pause_at_end=False)

    output = capsys.readouterr().out
    assert "DOI-specific enrichment skipped" in output
    assert "--- Generated BibTeX-like entry from available metadata ---" in output
    assert "citation key: starnini2025" in output


def test_metadata_display_prints_strings_without_python_repr_wrapping(capsys):
    long_title = "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"

    cli._print_selected_paper_metadata({
        "title": long_title,
        "authors": ["Devlin, Jacob"],
        "year": 2018,
        "venue": "",
        "publisher": "arXiv",
        "type": "Article",
        "cited_by_count": 75,
        "citation_source": "DataCite",
        "citation_sources": {"DataCite": 75},
        "metadata_sources": ["DataCite"],
        "doi": "10.48550/arXiv.1810.04805",
        "arxiv_id": "1810.04805",
        "openalex_id": "",
        "url": "https://arxiv.org/abs/1810.04805",
    })

    output = capsys.readouterr().out
    assert long_title in output
    assert "title: ('BERT" not in output
    assert "Understanding')" not in output
