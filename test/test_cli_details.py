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
    monkeypatch.setattr(cli, "get_best_structured_metadata", lambda doi: {"source": "Crossref", "doi": doi})
    monkeypatch.setattr(cli, "get_orcids_from_openalex", lambda doi: [])
    monkeypatch.setattr(
        cli,
        "get_bibtex_from_doi",
        lambda doi: "@article{Davies_2011, title = {Still building the memex}, year = {2011}}",
    )

    cli.print_selected_work_details(candidate, pause_at_end=False)

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
    monkeypatch.setattr(cli, "get_best_structured_metadata", lambda doi: {"source": "Crossref", "doi": doi})
    monkeypatch.setattr(cli, "get_orcids_from_openalex", lambda doi: [])
    monkeypatch.setattr(cli, "get_bibtex_from_doi", lambda doi: None)

    cli.print_selected_work_details(candidate, pause_at_end=False)

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

    cli.print_selected_work_details(candidate, pause_at_end=False)

    output = capsys.readouterr().out
    assert "DOI-specific enrichment skipped" in output
    assert "--- Generated BibTeX-like entry from available metadata ---" in output
    assert "citation key: starnini2025" in output
