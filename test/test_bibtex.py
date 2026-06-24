import smeli


def test_split_bibtex_fields_does_not_split_inside_braces_or_quotes():
    body = 'title = {A title, with comma}, author = "Doe, Jane and Smith, John", year = {2025}'
    assert smeli.bibtex._split_bibtex_fields(body) == [
        'title = {A title, with comma}',
        'author = "Doe, Jane and Smith, John"',
        'year = {2025}',
    ]


def test_parse_bibtex_entry_extracts_type_key_and_fields():
    bibtex = """
    @article{starnini2025opinion,
      title = {Opinion dynamics: Statistical physics and beyond},
      author = {Starnini, Michele and Baumann, Fabian},
      year = {2025},
      doi = {10.48550/arXiv.2507.11521},
      url = {https://arxiv.org/abs/2507.11521}
    }
    """
    parsed = smeli.parse_bibtex_entry(bibtex)
    assert parsed["entry_type"] == "article"
    assert parsed["cite_key"] == "starnini2025opinion"
    assert parsed["fields"]["title"] == "Opinion dynamics: Statistical physics and beyond"
    assert parsed["fields"]["doi"] == "10.48550/arXiv.2507.11521"


def test_parse_bibtex_entry_returns_none_for_non_entry():
    assert smeli.parse_bibtex_entry("not bibtex") is None


def test_make_cite_key_uses_first_author_surname_and_year():
    candidate = {
        "authors": ["Michele Starnini"],
        "year": 2025,
        "title": "Opinion dynamics: Statistical physics and beyond",
    }
    assert smeli.make_cite_key(candidate) == "starnini2025"


def test_make_cite_key_handles_comma_form_author_names():
    candidate = {
        "authors": ["Davies, Stephen"],
        "year": 2011,
        "title": "Still building the memex",
    }
    assert smeli.make_cite_key(candidate) == "davies2011"


def test_candidate_to_bibtex_includes_arxiv_fields_for_doi_less_arxiv_candidate():
    candidate = {
        "title": "Opinion dynamics: Statistical physics and beyond",
        "authors": ["Michele Starnini", "Fabian Baumann"],
        "year": 2025,
        "venue": "arXiv",
        "publisher": "arXiv",
        "doi": None,
        "arxiv_id": "2507.11521",
        "arxiv_category": "physics.soc-ph",
        "url": "https://arxiv.org/abs/2507.11521",
    }
    bibtex = smeli.candidate_to_bibtex(candidate)
    assert bibtex.startswith("@misc{")
    assert "eprint = {2507.11521}" in bibtex
    assert "archivePrefix = {arXiv}" in bibtex
    assert "primaryClass = {physics.soc-ph}" in bibtex
    assert "doi =" not in bibtex


def test_candidate_to_bibtex_includes_doi_when_present():
    candidate = {
        "title": "Modeling Echo Chambers and Polarization Dynamics in Social Networks",
        "authors": ["Fabian Baumann"],
        "year": 2020,
        "venue": "Physical Review Letters",
        "doi": "10.1103/PhysRevLett.124.048301",
        "url": "https://doi.org/10.1103/PhysRevLett.124.048301",
    }
    bibtex = smeli.candidate_to_bibtex(candidate)
    assert bibtex.startswith("@article{")
    assert "journal = {Physical Review Letters}" in bibtex
    assert "doi = {10.1103/PhysRevLett.124.048301}" in bibtex


def test_print_bibtex_pretty_prints_and_preserves_raw(capsys):
    bibtex = "@article{key, title = {My Title}, year = {2025}}"
    smeli.print_bibtex(bibtex)
    output = capsys.readouterr().out
    assert "BibTeX entry:" in output
    assert "type: article" in output
    assert "title: My Title" in output
    assert "Raw BibTeX:" in output
    assert "@article{key" in output
