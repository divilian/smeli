import smeli


def starnini_candidate():
    return {
        "title": "Opinion dynamics: Statistical physics and beyond",
        "authors": ["Michele Starnini"],
        "year": 2025,
        "doi": None,
        "arxiv_id": "2507.11521",
        "openalex_id": "https://openalex.org/W123",
        "venue": "arXiv",
        "publisher": "arXiv",
        "type": "article",
        "url": "https://arxiv.org/abs/2507.11521",
        "cited_by_count": 0,
        "metadata_sources": ["arXiv"],
        "source": "arXiv",
    }


def test_get_work_candidates_merges_and_sorts_regular_source_results(monkeypatch):
    calls = []

    def fake_openalex(**kwargs):
        calls.append(("openalex", kwargs))
        return [starnini_candidate() | {"source": "OpenAlex", "metadata_sources": ["OpenAlex"]}]

    def fake_crossref(**kwargs):
        calls.append(("crossref", kwargs))
        return []

    def fake_datacite(**kwargs):
        calls.append(("datacite", kwargs))
        return [starnini_candidate() | {"source": "DataCite", "metadata_sources": ["DataCite"], "doi": "10.48550/arXiv.2507.11521"}]

    def fake_arxiv(**kwargs):
        calls.append(("arxiv", kwargs))
        return []

    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_openalex", fake_openalex)
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_crossref", fake_crossref)
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_datacite", fake_datacite)
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_arxiv", fake_arxiv)

    results = smeli.get_work_candidates(author="starnini", title="opinion dynamics", year=2025)
    assert len(results) == 1
    assert results[0]["doi"] == "10.48550/arXiv.2507.11521"
    assert results[0]["metadata_sources"] == ["OpenAlex", "DataCite"]
    assert results[0]["score"] > 0
    assert {name for name, _ in calls} == {"openalex", "crossref", "datacite", "arxiv"}


def test_get_work_candidates_tries_swapped_title_author_when_strict_empty(monkeypatch):
    strict_calls = []

    def fake_openalex(**kwargs):
        strict_calls.append(kwargs)
        if kwargs.get("author") == "starnini" and kwargs.get("title") == "opinion dynamics":
            return [starnini_candidate()]
        return []

    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_openalex", fake_openalex)
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_crossref", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_datacite", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_arxiv", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_openalex_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_crossref_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_datacite_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_arxiv_loose", lambda *args, **kwargs: [])

    results = smeli.get_work_candidates(author="opinion dynamics", title="starnini")
    assert len(results) == 1
    assert results[0]["match_note"] == "title/author swapped"
    assert {"author": "opinion dynamics", "title": "starnini", "year": None} in strict_calls
    assert {"author": "starnini", "title": "opinion dynamics", "year": None} in strict_calls


def test_get_work_candidates_tries_loose_fallback_when_fielded_empty(monkeypatch):
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_openalex", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_crossref", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_datacite", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_arxiv", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_openalex_loose", lambda query, **kwargs: [starnini_candidate()] if query == "starnini opinion dynamics" else [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_crossref_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_datacite_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_work_candidates_from_arxiv_loose", lambda *args, **kwargs: [])

    results = smeli.get_work_candidates(author="opinion dynamics", title="starnini")
    assert len(results) == 1
    # Swapped fallback is tried before loose fallback, but the loose fallback is
    # the one that returns a candidate in this test.
    assert results[0]["match_note"] == "broad all-fields fallback"


def test_get_work_candidates_from_identifier_dispatches_doi_arxiv_openalex(monkeypatch):
    monkeypatch.setattr(smeli.sources, "get_candidate_from_doi", lambda value: {"doi": smeli.clean_doi(value), "title": "DOI work"})
    monkeypatch.setattr(smeli.sources, "get_candidate_from_arxiv_id", lambda value: {"arxiv_id": smeli.base_arxiv_id(value), "title": "arXiv work"})
    monkeypatch.setattr(smeli.sources, "get_candidate_from_openalex_id", lambda value: {"openalex_id": value, "title": "OpenAlex work"})

    assert smeli.get_work_candidates_from_identifier("https://doi.org/10.1234/foo")[0]["doi"] == "10.1234/foo"
    assert smeli.get_work_candidates_from_identifier("https://arxiv.org/abs/2507.11521v1")[0]["arxiv_id"] == "2507.11521"
    assert smeli.get_work_candidates_from_identifier("W123")[0]["openalex_id"] == "W123"
