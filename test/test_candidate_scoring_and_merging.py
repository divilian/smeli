import doi


def make_candidate(**overrides):
    candidate = {
        "title": "Opinion dynamics: Statistical physics and beyond",
        "authors": ["Michele Starnini", "Fabian Baumann"],
        "year": 2025,
        "doi": None,
        "arxiv_id": "2507.11521",
        "openalex_id": "https://openalex.org/W123",
        "venue": "arXiv",
        "publisher": "arXiv",
        "type": "article",
        "url": "https://arxiv.org/abs/2507.11521",
        "cited_by_count": 7,
        "metadata_sources": ["OpenAlex"],
    }
    candidate.update(overrides)
    return candidate


def test_candidate_score_rewards_title_author_year_and_identifiers():
    score, cites = doi.candidate_score(make_candidate(), title="opinion dynamics", author="starnini", year=2025)
    assert score >= 100
    assert cites == 7


def test_add_best_candidate_score_ignores_private_match_note_key():
    candidate = make_candidate()
    doi.add_best_candidate_score(
        candidate,
        [
            {"title": "starnini", "author": "opinion dynamics", "year": None},
            {"title": "opinion dynamics", "author": "starnini", "year": None, "_match_note": "title/author swapped"},
        ],
    )
    assert candidate["score"] > 0
    assert candidate["match_note"] == "title/author swapped"


def test_candidates_are_same_by_doi_arxiv_openalex_or_strong_metadata():
    base = make_candidate(doi="10.48550/arXiv.2507.11521")
    assert doi.candidates_are_same(base, make_candidate(doi="https://doi.org/10.48550/arXiv.2507.11521"))
    assert doi.candidates_are_same(base, make_candidate(doi=None, arxiv_id="2507.11521v2"))
    assert doi.candidates_are_same(base, make_candidate(doi=None, arxiv_id=None, openalex_id="https://openalex.org/W123"))
    assert doi.candidates_are_same(
        make_candidate(doi=None, arxiv_id=None, openalex_id="", metadata_sources=["Crossref"]),
        make_candidate(doi=None, arxiv_id=None, openalex_id="", metadata_sources=["DataCite"]),
    )


def test_merge_candidates_fills_missing_fields_and_preserves_sources():
    primary = make_candidate(doi=None, authors=[], metadata_sources=["OpenAlex"], cited_by_count=1)
    secondary = make_candidate(doi="10.48550/arXiv.2507.11521", authors=["Michele Starnini"], metadata_sources=["DataCite"], cited_by_count=5)
    merged = doi.merge_candidates(primary, secondary)
    assert merged["doi"] == "10.48550/arXiv.2507.11521"
    assert merged["authors"] == ["Michele Starnini"]
    assert merged["cited_by_count"] == 5
    assert merged["metadata_sources"] == ["OpenAlex", "DataCite"]


def test_merge_candidate_list_deduplicates_related_records():
    candidates = [
        make_candidate(source="OpenAlex", metadata_sources=["OpenAlex"]),
        make_candidate(source="arXiv", metadata_sources=["arXiv"], openalex_id="", arxiv_id="2507.11521v1"),
    ]
    merged = doi.merge_candidate_list(candidates)
    assert len(merged) == 1
    assert merged[0]["metadata_sources"] == ["OpenAlex", "arXiv"]
