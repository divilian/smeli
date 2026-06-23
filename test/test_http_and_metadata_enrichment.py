import requests

import doi


class FakeResponse:
    def __init__(self, json_data=None, text="", status_error=None):
        self._json_data = json_data
        self.text = text
        self.reason = "Boom"
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


def test_fetch_response_merges_headers_and_timeout(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse(json_data={"ok": True})

    monkeypatch.setattr(doi.requests, "get", fake_get)
    response = doi.fetch_response("https://example.org", source="test", headers={"Accept": "text/plain"}, timeout=3)
    assert response is not None
    assert captured["kwargs"]["timeout"] == 3
    assert captured["kwargs"]["headers"]["Accept"] == "text/plain"
    assert "User-Agent" in captured["kwargs"]["headers"]


def test_fetch_json_returns_none_on_invalid_json(monkeypatch, capsys):
    monkeypatch.setattr(doi, "fetch_response", lambda *args, **kwargs: FakeResponse(json_data=ValueError("bad json")))
    assert doi.fetch_json("https://example.org", source="Broken") is None
    assert "not valid JSON" in capsys.readouterr().out


def test_get_metadata_from_crossref_shapes_response(monkeypatch):
    def fake_fetch_json(url, *, source="request", **kwargs):
        return {
            "message": {
                "DOI": "10.1103/PhysRevLett.124.048301",
                "title": ["Modeling Echo Chambers and Polarization Dynamics in Social Networks"],
                "author": [{"given": "Fabian", "family": "Baumann"}],
                "container-title": ["Physical Review Letters"],
                "publisher": "American Physical Society",
                "is-referenced-by-count": 100,
                "issued": {"date-parts": [[2020]]},
                "type": "journal-article",
                "URL": "https://doi.org/10.1103/PhysRevLett.124.048301",
            }
        }

    monkeypatch.setattr(doi, "fetch_json", fake_fetch_json)
    metadata = doi.get_metadata_from_crossref("10.1103/PhysRevLett.124.048301")
    assert metadata["source"] == "Crossref"
    assert metadata["year"] == 2020
    assert metadata["authors"] == ["Fabian Baumann"]


def test_get_metadata_from_datacite_shapes_response(monkeypatch):
    def fake_fetch_json(url, *, source="request", **kwargs):
        return {
            "data": {
                "id": "10.48550/arXiv.2507.11521",
                "attributes": {
                    "doi": "10.48550/arXiv.2507.11521",
                    "titles": [{"title": "Opinion dynamics: Statistical physics and beyond"}],
                    "creators": [{"name": "Starnini, Michele"}],
                    "publisher": "arXiv",
                    "publicationYear": 2025,
                    "types": {"resourceTypeGeneral": "Preprint"},
                    "url": "https://arxiv.org/abs/2507.11521",
                    "citationCount": 3,
                },
            }
        }

    monkeypatch.setattr(doi, "fetch_json", fake_fetch_json)
    metadata = doi.get_metadata_from_datacite("10.48550/arXiv.2507.11521")
    assert metadata["source"] == "DataCite"
    assert metadata["year"] == 2025
    assert metadata["type"] == "Preprint"


def test_get_best_structured_metadata_falls_back_to_datacite(monkeypatch):
    monkeypatch.setattr(doi, "get_metadata_from_crossref", lambda value: None)
    monkeypatch.setattr(doi, "get_metadata_from_datacite", lambda value: {"source": "DataCite", "doi": value})
    assert doi.get_best_structured_metadata("10.48550/arXiv.2507.11521")["source"] == "DataCite"


def test_get_bibtex_from_doi_uses_doi_org_accept_header(monkeypatch):
    captured = {}

    def fake_fetch_text(url, *, source="request", **kwargs):
        captured["url"] = url
        captured["source"] = source
        captured["headers"] = kwargs.get("headers", {})
        return "@article{key}"

    monkeypatch.setattr(doi, "fetch_text", fake_fetch_text)
    assert doi.get_bibtex_from_doi("10.1234/abc def") == "@article{key}"
    assert captured["url"].endswith("10.1234/abc%20def")
    assert captured["headers"]["Accept"] == "application/x-bibtex"
