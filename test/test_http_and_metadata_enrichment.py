import requests

import smeli


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

    monkeypatch.setattr(smeli.http.requests, "get", fake_get)
    response = smeli.http._fetch_response("https://example.org", source="test", headers={"Accept": "text/plain"}, timeout=3)
    assert response is not None
    assert captured["kwargs"]["timeout"] == 3
    assert captured["kwargs"]["headers"]["Accept"] == "text/plain"
    assert "User-Agent" in captured["kwargs"]["headers"]


def test_fetch_json_returns_none_on_invalid_json(monkeypatch, capsys):
    monkeypatch.setattr(smeli.http, "_fetch_response", lambda *args, **kwargs: FakeResponse(json_data=ValueError("bad json")))
    assert smeli.http._fetch_json("https://example.org", source="Broken") is None
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

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)
    metadata = smeli.get_metadata_from_crossref("10.1103/PhysRevLett.124.048301")
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

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)
    metadata = smeli.get_metadata_from_datacite("10.48550/arXiv.2507.11521")
    assert metadata["source"] == "DataCite"
    assert metadata["year"] == 2025
    assert metadata["type"] == "Preprint"


def test_get_best_structured_metadata_falls_back_to_datacite(monkeypatch):
    monkeypatch.setattr(smeli.sources, "get_metadata_from_crossref", lambda value: None)
    monkeypatch.setattr(smeli.sources, "get_metadata_from_datacite", lambda value: {"source": "DataCite", "doi": value})
    assert smeli.get_best_structured_metadata("10.48550/arXiv.2507.11521")["source"] == "DataCite"


def test_get_bibtex_from_doi_uses_doi_org_accept_header(monkeypatch):
    captured = {}

    def fake_fetch_text(url, *, source="request", **kwargs):
        captured["url"] = url
        captured["source"] = source
        captured["headers"] = kwargs.get("headers", {})
        return "@article{key}"

    monkeypatch.setattr(smeli.sources, "_fetch_text", fake_fetch_text)
    assert smeli.get_bibtex_from_doi("10.1234/abc def") == "@article{key}"
    assert captured["url"].endswith("10.1234/abc%20def")
    assert captured["headers"]["Accept"] == "application/x-bibtex"


def test_fetch_response_can_silence_expected_statuses(monkeypatch, capsys):
    response = FakeResponse()
    response.status_code = 404
    response.reason = "Not Found"
    response.status_error = requests.HTTPError(response=response)

    monkeypatch.setattr(smeli.http.requests, "get", lambda *args, **kwargs: response)

    assert smeli.http._fetch_response("https://example.org/missing", source="DataCite", quiet_statuses={404}) is None
    assert capsys.readouterr().out == ""


def test_get_metadata_from_datacite_silences_404(monkeypatch, capsys):
    captured = {}

    def fake_fetch_json(url, *, source="request", **kwargs):
        captured["kwargs"] = kwargs
        return None

    monkeypatch.setattr(smeli.sources, "_fetch_json", fake_fetch_json)

    assert smeli.get_metadata_from_datacite("10.1145/1897816.1897840") is None
    assert captured["kwargs"]["quiet_statuses"] == {404}
    assert capsys.readouterr().out == ""
