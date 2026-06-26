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


def test_get_paper_candidates_merges_and_sorts_regular_source_results(monkeypatch):
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

    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_openalex", fake_openalex)
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_crossref", fake_crossref)
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_datacite", fake_datacite)
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_arxiv", fake_arxiv)

    results = smeli.get_paper_candidates(author="starnini", title="opinion dynamics", year=2025)
    assert len(results) == 1
    assert results[0]["doi"] == "10.48550/arXiv.2507.11521"
    assert results[0]["metadata_sources"] == ["OpenAlex", "DataCite"]
    assert results[0]["score"] > 0
    assert {name for name, _ in calls} == {"openalex", "crossref", "datacite", "arxiv"}


def test_get_paper_candidates_tries_swapped_title_author_when_strict_empty(monkeypatch):
    strict_calls = []

    def fake_openalex(**kwargs):
        strict_calls.append(kwargs)
        if kwargs.get("author") == "starnini" and kwargs.get("title") == "opinion dynamics":
            return [starnini_candidate()]
        return []

    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_openalex", fake_openalex)
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_crossref", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_datacite", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_arxiv", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_openalex_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_crossref_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_datacite_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_arxiv_loose", lambda *args, **kwargs: [])

    results = smeli.get_paper_candidates(author="opinion dynamics", title="starnini")
    assert len(results) == 1
    assert results[0]["match_note"] == "title/author swapped"
    assert {"author": "opinion dynamics", "title": "starnini", "year": None} in strict_calls
    assert {"author": "starnini", "title": "opinion dynamics", "year": None} in strict_calls


def test_get_paper_candidates_tries_loose_fallback_when_fielded_empty(monkeypatch):
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_openalex", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_crossref", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_datacite", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_arxiv", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_openalex_loose", lambda query, **kwargs: [starnini_candidate()] if query == "starnini opinion dynamics" else [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_crossref_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_datacite_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_arxiv_loose", lambda *args, **kwargs: [])

    results = smeli.get_paper_candidates(author="opinion dynamics", title="starnini")
    assert len(results) == 1
    # Swapped fallback is tried before loose fallback, but the loose fallback is
    # the one that returns a candidate in this test.
    assert results[0]["match_note"] == "broad all-fields fallback"


def test_get_paper_candidates_from_identifier_dispatches_doi_arxiv_orcid_openalex(monkeypatch):
    monkeypatch.setattr(smeli.sources, "get_candidate_from_doi", lambda value: {"doi": smeli.clean_doi(value), "title": "DOI paper"})
    monkeypatch.setattr(smeli.sources, "get_candidate_from_arxiv_id", lambda value: {"arxiv_id": smeli.base_arxiv_id(value), "title": "arXiv paper"})
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_orcid", lambda value: [{"orcid": smeli.extract_orcid(value), "title": "ORCID paper"}])
    monkeypatch.setattr(smeli.sources, "get_candidate_from_openalex_id", lambda value: {"openalex_id": value, "title": "OpenAlex paper"})

    assert smeli.get_paper_candidates_from_identifier("https://doi.org/10.1234/foo")[0]["doi"] == "10.1234/foo"
    assert smeli.get_paper_candidates_from_identifier("https://arxiv.org/abs/2507.11521v1")[0]["arxiv_id"] == "2507.11521"
    assert smeli.get_paper_candidates_from_identifier("https://orcid.org/0000-0002-0254-6627")[0]["orcid"] == "0000-0002-0254-6627"
    assert smeli.get_paper_candidates_from_identifier("W123")[0]["openalex_id"] == "W123"


def test_get_paper_candidates_uses_loose_sources_for_free_form_query(monkeypatch):
    calls = []

    def fake_openalex_loose(query, **kwargs):
        calls.append(("openalex", query, kwargs))
        return [starnini_candidate()] if query == "starnini opinion dynamics" else []

    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_openalex", lambda **kwargs: (_ for _ in ()).throw(AssertionError("strict OpenAlex should not be used for query")))
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_crossref", lambda **kwargs: (_ for _ in ()).throw(AssertionError("strict Crossref should not be used for query")))
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_datacite", lambda **kwargs: (_ for _ in ()).throw(AssertionError("strict DataCite should not be used for query")))
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_arxiv", lambda **kwargs: (_ for _ in ()).throw(AssertionError("strict arXiv should not be used for query")))
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_openalex_loose", fake_openalex_loose)
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_crossref_loose", lambda query, **kwargs: calls.append(("crossref", query, kwargs)) or [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_datacite_loose", lambda query, **kwargs: calls.append(("datacite", query, kwargs)) or [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_arxiv_loose", lambda query, **kwargs: calls.append(("arxiv", query, kwargs)) or [])

    results = smeli.get_paper_candidates(query="starnini opinion dynamics", year=2025)

    assert len(results) == 1
    assert results[0]["match_note"] == "free-form query"
    assert {name for name, _, _ in calls} == {"openalex", "crossref", "datacite", "arxiv"}
    assert all(query == "starnini opinion dynamics" for _, query, _ in calls)


def test_get_paper_candidates_is_quiet_by_default(monkeypatch, capsys):
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_openalex", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_crossref", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_datacite", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_arxiv", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_openalex_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_crossref_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_datacite_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_arxiv_loose", lambda *args, **kwargs: [])

    smeli.get_paper_candidates(author="clemmer", title="smeagol")

    output = capsys.readouterr().out
    assert output == ""


def test_get_paper_candidates_can_report_progress_to_callback(monkeypatch):
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_openalex", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_crossref", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_datacite", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_arxiv", lambda **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_openalex_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_crossref_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_datacite_loose", lambda *args, **kwargs: [])
    monkeypatch.setattr(smeli.sources, "_get_paper_candidates_from_arxiv_loose", lambda *args, **kwargs: [])
    messages = []

    smeli.get_paper_candidates(author="clemmer", title="smeagol", progress=messages.append)

    assert "  OpenAlex..." in messages
    assert "  Crossref..." in messages
    assert "  DataCite..." in messages
    assert "  arXiv..." in messages


def test_arxiv_datacite_doi_candidate_gets_openalex_bibliographic_enrichment(monkeypatch):
    def fake_datacite(value):
        assert value == "10.48550/arXiv.1810.04805"
        return {
            "source": "DataCite",
            "doi": value,
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "authors": ["Devlin, Jacob", "Chang, Ming-Wei", "Lee, Kenton", "Toutanova, Kristina"],
            "journal": "",
            "publisher": "arXiv",
            "citations": 75,
            "year": 2018,
            "type": "Article",
            "url": "https://arxiv.org/abs/1810.04805",
        }

    def fake_openalex_search(**kwargs):
        assert kwargs["title"] == "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
        assert kwargs["author"] == "devlin"
        assert kwargs["year"] is None
        return [
            {
                "source": "OpenAlex",
                "metadata_sources": ["OpenAlex"],
                "doi": "10.18653/v1/N19-1423",
                "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
                "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
                "year": 2019,
                "venue": "NAACL",
                "publisher": "ACL",
                "cited_by_count": 172572,
                "openalex_id": "https://openalex.org/W2963341956",
                "arxiv_id": "",
                "url": "https://aclanthology.org/N19-1423/",
            }
        ]

    monkeypatch.setattr(smeli.sources, "get_metadata_from_crossref", lambda value: None)
    monkeypatch.setattr(smeli.sources, "get_metadata_from_datacite", fake_datacite)
    monkeypatch.setattr(smeli.sources, "_get_candidate_from_openalex_doi", lambda value: None)
    monkeypatch.setattr(smeli.sources, "get_paper_candidates_from_openalex", fake_openalex_search)

    candidate = smeli.get_candidate_from_doi("10.48550/arXiv.1810.04805")

    assert candidate["doi"] == "10.48550/arXiv.1810.04805"
    assert candidate["arxiv_id"] == "1810.04805"
    assert candidate["openalex_id"] == "https://openalex.org/W2963341956"
    assert candidate["cited_by_count"] == 172572
    assert candidate["metadata_sources"] == ["DataCite", "OpenAlex"]


def test_arxiv_datacite_doi_metadata_uses_enriched_candidate(monkeypatch):
    monkeypatch.setattr(
        smeli.sources,
        "get_candidate_from_doi",
        lambda value: {
            "source": "DataCite",
            "metadata_sources": ["DataCite", "OpenAlex"],
            "doi": value,
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "authors": ["Devlin, Jacob"],
            "venue": "",
            "publisher": "arXiv",
            "cited_by_count": 172572,
            "year": 2018,
            "type": "Article",
            "url": "https://arxiv.org/abs/1810.04805",
            "arxiv_id": "1810.04805",
            "openalex_id": "https://openalex.org/W2963341956",
        },
    )

    metadata = smeli.get_metadata("10.48550/arXiv.1810.04805")

    assert metadata["citations"] == 172572
    assert metadata["metadata_sources"] == ["DataCite", "OpenAlex"]
    assert metadata["openalex_id"] == "https://openalex.org/W2963341956"
