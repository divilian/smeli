import smeli


def test_get_paper_candidates_from_openalex_uses_fetch_json_and_keeps_doi_less(monkeypatch):
    captured = {}

    def fake_fetch_json(url, *, source="request", **kwargs):
        captured["url"] = url
        captured["source"] = source
        captured["kwargs"] = kwargs
        return {
            "results": [
                {
                    "id": "https://openalex.org/W123",
                    "doi": None,
                    "ids": {},
                    "title": "Opinion dynamics: Statistical physics and beyond",
                    "publication_year": 2025,
                    "authorships": [{"author": {"display_name": "Michele Starnini"}}],
                    "primary_location": {"landing_page_url": "https://arxiv.org/abs/2507.11521", "source": {"display_name": "arXiv"}},
                    "cited_by_count": 0,
                    "type": "article",
                }
            ]
        }

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)
    results = smeli.get_paper_candidates_from_openalex(author="starnini", title="opinion dynamics", year=2025)
    assert captured["source"] == "OpenAlex"
    assert captured["kwargs"]["params"]["search"] == "opinion dynamics"
    assert results[0]["doi"] is None
    assert results[0]["arxiv_id"] == "2507.11521"


def test_get_paper_candidates_from_crossref_converts_and_filters(monkeypatch):
    def fake_fetch_json(url, *, source="request", **kwargs):
        return {
            "message": {
                "items": [
                    {
                        "DOI": "10.1103/PhysRevLett.124.048301",
                        "title": ["Modeling Echo Chambers and Polarization Dynamics in Social Networks"],
                        "issued": {"date-parts": [[2020]]},
                        "author": [{"given": "Fabian", "family": "Baumann"}],
                        "container-title": ["Physical Review Letters"],
                        "is-referenced-by-count": 10,
                        "URL": "https://doi.org/10.1103/PhysRevLett.124.048301",
                    },
                    {
                        "DOI": "10.bad/notmatch",
                        "title": ["Unrelated title"],
                        "issued": {"date-parts": [[2020]]},
                        "author": [{"given": "Someone", "family": "Else"}],
                    },
                ]
            }
        }

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)
    results = smeli.get_paper_candidates_from_crossref(author="Baumann", title="echo chambers", year=2020)
    assert len(results) == 1
    assert results[0]["doi"] == "10.1103/PhysRevLett.124.048301"


def test_get_paper_candidates_from_datacite_converts_and_filters(monkeypatch):
    def fake_fetch_json(url, *, source="request", **kwargs):
        return {
            "data": [
                {
                    "id": "10.48550/arXiv.2507.11521",
                    "attributes": {
                        "doi": "10.48550/arXiv.2507.11521",
                        "titles": [{"title": "Opinion dynamics: Statistical physics and beyond"}],
                        "publicationYear": 2025,
                        "creators": [{"name": "Starnini, Michele"}],
                        "publisher": "arXiv",
                        "url": "https://arxiv.org/abs/2507.11521",
                    },
                }
            ]
        }

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)
    results = smeli.get_paper_candidates_from_datacite(author="starnini", title="opinion dynamics", year=2025)
    assert len(results) == 1
    assert results[0]["doi"] == "10.48550/arXiv.2507.11521"


def test_get_paper_candidates_from_arxiv_parses_atom(monkeypatch):
    atom = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2507.11521v1</id>
        <title>Opinion dynamics: Statistical physics and beyond</title>
        <published>2025-07-15T00:00:00Z</published>
        <author><name>Michele Starnini</name></author>
        <link href="http://arxiv.org/abs/2507.11521v1" rel="alternate" />
        <arxiv:primary_category term="physics.soc-ph" />
      </entry>
    </feed>
    """

    def fake_fetch_text(url, *, source="request", **kwargs):
        return atom

    monkeypatch.setattr(smeli.sources, "_fetch_text", fake_fetch_text)
    results = smeli.get_paper_candidates_from_arxiv(author="starnini", title="opinion dynamics", year=2025)
    assert len(results) == 1
    assert results[0]["arxiv_id"] == "2507.11521"


def test_get_paper_candidates_from_orcid_uses_openalex_orcid_filter(monkeypatch):
    captured = {}

    def fake_fetch_json(url, *, source="request", **kwargs):
        captured["url"] = url
        captured["source"] = source
        captured["kwargs"] = kwargs
        return {
            "results": [
                {
                    "id": "https://openalex.org/W999",
                    "doi": "https://doi.org/10.1145/1897816.1897840",
                    "ids": {"doi": "https://doi.org/10.1145/1897816.1897840"},
                    "title": "Still building the memex",
                    "publication_year": 2011,
                    "authorships": [
                        {"author": {"display_name": "Stephen Davies", "orcid": "https://orcid.org/0000-0002-0254-6627"}}
                    ],
                    "primary_location": {
                        "landing_page_url": "https://doi.org/10.1145/1897816.1897840",
                        "source": {"display_name": "Communications of the ACM"},
                    },
                    "cited_by_count": 7,
                    "type": "article",
                }
            ]
        }

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)
    results = smeli.get_paper_candidates_from_orcid("0000-0002-0254-6627")

    assert captured["source"] == "OpenAlex"
    assert captured["kwargs"]["params"]["filter"] == "authorships.author.orcid:0000-0002-0254-6627"
    assert captured["kwargs"]["params"]["sort"] == "publication_date:desc"
    assert results[0]["title"] == "Still building the memex"
    assert results[0]["match_note"] == "ORCID 0000-0002-0254-6627"


def test_search_orcids_uses_openalex_author_search_and_returns_orcid_records(monkeypatch):
    captured = {}

    def fake_fetch_json(url, *, source="request", **kwargs):
        captured["url"] = url
        captured["source"] = source
        captured["kwargs"] = kwargs
        return {
            "results": [
                {
                    "id": "https://openalex.org/A123",
                    "display_name": "Stephen Davies",
                    "orcid": "https://orcid.org/0000-0002-0254-6627",
                    "works_count": 12,
                    "cited_by_count": 34,
                    "last_known_institutions": [
                        {"display_name": "University of Mary Washington"}
                    ],
                    "relevance_score": 98.7,
                },
                {
                    "id": "https://openalex.org/A999",
                    "display_name": "Stephen Davies Without Orcid",
                    "works_count": 1,
                },
            ]
        }

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)

    results = smeli.search_orcids("Stephen Davies")

    assert captured["url"] == "https://api.openalex.org/authors"
    assert captured["source"] == "OpenAlex"
    assert captured["kwargs"]["params"]["search"] == "Stephen Davies"
    assert captured["kwargs"]["params"]["per-page"] == 10
    assert results == [
        {
            "name": "Stephen Davies",
            "orcid": "0000-0002-0254-6627",
            "orcid_url": "https://orcid.org/0000-0002-0254-6627",
            "openalex_id": "https://openalex.org/A123",
            "affiliation": "University of Mary Washington",
            "affiliations": ["University of Mary Washington"],
            "works_count": 12,
            "cited_by_count": 34,
            "source": "OpenAlex",
            "relevance": 98.7,
        }
    ]


def test_search_orcids_applies_affiliation_filter_and_deduplicates(monkeypatch):
    def fake_fetch_json(url, *, source="request", **kwargs):
        return {
            "results": [
                {
                    "id": "https://openalex.org/A1",
                    "display_name": "Ada Lovelace",
                    "orcid": "https://orcid.org/0000-0002-0254-6627",
                    "last_known_institutions": [{"display_name": "Wrong University"}],
                },
                {
                    "id": "https://openalex.org/A2",
                    "display_name": "Ada Lovelace",
                    "orcid": "https://orcid.org/0000-0002-0254-6627",
                    "affiliations": [
                        {"institution": {"display_name": "University of Mary Washington"}}
                    ],
                },
                {
                    "id": "https://openalex.org/A3",
                    "display_name": "Ada Byron",
                    "orcid": "https://orcid.org/0000-0001-2345-678X",
                    "last_known_institutions": [{"display_name": "University of Mary Washington"}],
                },
            ]
        }

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)

    results = smeli.search_orcids("Ada", affiliation="mary washington", max_results=5)

    assert [result["orcid"] for result in results] == [
        "0000-0002-0254-6627",
        "0000-0001-2345-678X",
    ]


def test_search_orcids_returns_empty_for_blank_name_without_request(monkeypatch):
    def fail_fetch_json(*args, **kwargs):
        raise AssertionError("should not request OpenAlex for a blank author name")

    monkeypatch.setattr(smeli.sources, "_fetch_json", fail_fetch_json)

    assert smeli.search_orcids("  ") == []
