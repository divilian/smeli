import smeli


def test_clean_doi_strips_common_prefixes_and_trailing_punctuation():
    assert smeli.clean_doi("https://doi.org/10.1234/ABC.567.") == "10.1234/ABC.567"
    assert smeli.clean_doi("doi:10.5555/example)") == "10.5555/example"
    assert smeli.clean_doi("  http://dx.doi.org/10.9/foo; ") == "10.9/foo"


def test_looks_like_doi_accepts_doi_urls_and_rejects_non_dois():
    assert smeli.looks_like_doi("https://doi.org/10.1145/1234567.1234568")
    assert smeli.looks_like_doi("10.48550/arXiv.2507.11521")
    assert not smeli.looks_like_doi("2507.11521")
    assert not smeli.looks_like_doi("https://arxiv.org/abs/2507.11521")


def test_quote_doi_helpers_use_correct_url_escaping():
    raw = "10.1145/abc def"
    assert smeli.normalize._quote_doi_for_path(raw) == "10.1145%2Fabc%20def"
    assert smeli.normalize._quote_doi_for_doi_org(raw) == "10.1145/abc%20def"


def test_normalize_for_match_removes_case_accents_punctuation_and_html():
    assert smeli.normalize._normalize_for_match("Caf&eacute;: Opinion-Dynamics!") == "cafe opinion dynamics"
    assert smeli.normalize._contains_normalized("Opinion dynamics: Statistical physics and beyond", "opinion dynamics")


def test_title_similarity_and_split_words_are_useful_for_matching():
    assert smeli.normalize._title_similarity("Opinion Dynamics", "opinion dynamics") == 1.0
    assert smeli.normalize._title_similarity("Opinion dynamics: Statistical physics", "Opinion dynamics statistical physics") > 0.85
    assert smeli.normalize._split_words("The opinion dynamics of a network") == {"opinion", "dynamics", "network"}


def test_orcid_helpers_accept_bare_prefixed_and_url_forms():
    assert smeli.extract_orcid("0000-0002-0254-6627") == "0000-0002-0254-6627"
    assert smeli.extract_orcid("orcid:0000-0002-0254-662x") == "0000-0002-0254-662X"
    assert smeli.extract_orcid("https://orcid.org/0000-0002-0254-6627") == "0000-0002-0254-6627"
    assert smeli.looks_like_orcid("https://orcid.org/0000-0002-0254-6627")
    assert smeli.orcid_url("0000-0002-0254-6627") == "https://orcid.org/0000-0002-0254-6627"
    assert not smeli.looks_like_orcid("not an orcid")


def test_extract_orcid_accepts_candidate_records():
    assert smeli.extract_orcid({"orcid": "https://orcid.org/0000-0002-0254-6627"}) == "0000-0002-0254-6627"
    assert smeli.extract_orcid({"authors": [{"name": "Ada"}, {"ORCID": "0000-0002-0254-662x"}]}) == "0000-0002-0254-662X"
    assert smeli.extract_orcid({"authors": [{"name": "Ada"}]}) is None
