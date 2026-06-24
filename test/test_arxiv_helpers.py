import smeli


def test_extract_arxiv_id_from_common_forms():
    assert smeli.extract_arxiv_id("https://arxiv.org/abs/2507.11521v1") == "2507.11521v1"
    assert smeli.extract_arxiv_id("https://arxiv.org/pdf/2507.11521.pdf") == "2507.11521"
    assert smeli.extract_arxiv_id("arXiv:2507.11521") == "2507.11521"
    assert smeli.extract_arxiv_id("old id cs/9901001v2") == "cs/9901001v2"


def test_base_arxiv_id_strips_version_suffix():
    assert smeli.base_arxiv_id("2507.11521v3") == "2507.11521"
    assert smeli.base_arxiv_id("cs/9901001v2") == "cs/9901001"


def test_find_arxiv_id_in_nested_mapping():
    mapping = {
        "ids": {"other": "none"},
        "locations": [
            {"landing_page_url": "https://example.org/nope"},
            {"landing_page_url": "https://arxiv.org/abs/2507.11521v1"},
        ],
    }
    assert smeli.normalize._find_arxiv_id_in_mapping(mapping) == "2507.11521v1"


def test_make_arxiv_url():
    assert smeli.make_arxiv_url("2507.11521") == "https://arxiv.org/abs/2507.11521"
    assert smeli.make_arxiv_url(None) == ""


def test_arxiv_loose_search_query_uses_normalized_terms():
    query = smeli.sources._arxiv_loose_search_query("Starnini opinion dynamics")
    assert 'all:"starnini"' in query
    assert 'all:"opinion"' in query
    assert 'all:"dynamics"' in query
