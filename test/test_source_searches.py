import doi


def test_get_work_candidates_from_openalex_uses_fetch_json_and_keeps_doi_less(monkeypatch):
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

    monkeypatch.setattr(doi, "fetch_json", fake_fetch_json)
    results = doi.get_work_candidates_from_openalex(author="starnini", title="opinion dynamics", year=2025)
    assert captured["source"] == "OpenAlex"
    assert captured["kwargs"]["params"]["search"] == "opinion dynamics"
    assert results[0]["doi"] is None
    assert results[0]["arxiv_id"] == "2507.11521"


def test_get_work_candidates_from_crossref_converts_and_filters(monkeypatch):
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

    monkeypatch.setattr(doi, "fetch_json", fake_fetch_json)
    results = doi.get_work_candidates_from_crossref(author="Baumann", title="echo chambers", year=2020)
    assert len(results) == 1
    assert results[0]["doi"] == "10.1103/PhysRevLett.124.048301"


def test_get_work_candidates_from_datacite_converts_and_filters(monkeypatch):
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

    monkeypatch.setattr(doi, "fetch_json", fake_fetch_json)
    results = doi.get_work_candidates_from_datacite(author="starnini", title="opinion dynamics", year=2025)
    assert len(results) == 1
    assert results[0]["doi"] == "10.48550/arXiv.2507.11521"


def test_get_work_candidates_from_arxiv_parses_atom(monkeypatch):
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

    monkeypatch.setattr(doi, "fetch_text", fake_fetch_text)
    results = doi.get_work_candidates_from_arxiv(author="starnini", title="opinion dynamics", year=2025)
    assert len(results) == 1
    assert results[0]["arxiv_id"] == "2507.11521"
