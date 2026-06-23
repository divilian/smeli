import doi


def test_clean_doi_strips_common_prefixes_and_trailing_punctuation():
    assert doi.clean_doi("https://doi.org/10.1234/ABC.567.") == "10.1234/ABC.567"
    assert doi.clean_doi("doi:10.5555/example)") == "10.5555/example"
    assert doi.clean_doi("  http://dx.doi.org/10.9/foo; ") == "10.9/foo"


def test_looks_like_doi_accepts_doi_urls_and_rejects_non_dois():
    assert doi.looks_like_doi("https://doi.org/10.1145/1234567.1234568")
    assert doi.looks_like_doi("10.48550/arXiv.2507.11521")
    assert not doi.looks_like_doi("2507.11521")
    assert not doi.looks_like_doi("https://arxiv.org/abs/2507.11521")


def test_quote_doi_helpers_use_correct_url_escaping():
    raw = "10.1145/abc def"
    assert doi.quote_doi_for_path(raw) == "10.1145%2Fabc%20def"
    assert doi.quote_doi_for_doi_org(raw) == "10.1145/abc%20def"


def test_normalize_for_match_removes_case_accents_punctuation_and_html():
    assert doi.normalize_for_match("Caf&eacute;: Opinion-Dynamics!") == "cafe opinion dynamics"
    assert doi.contains_normalized("Opinion dynamics: Statistical physics and beyond", "opinion dynamics")


def test_title_similarity_and_split_words_are_useful_for_matching():
    assert doi.title_similarity("Opinion Dynamics", "opinion dynamics") == 1.0
    assert doi.title_similarity("Opinion dynamics: Statistical physics", "Opinion dynamics statistical physics") > 0.85
    assert doi.split_words("The opinion dynamics of a network") == {"opinion", "dynamics", "network"}
