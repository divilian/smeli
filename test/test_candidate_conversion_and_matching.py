import xml.etree.ElementTree as ET

import doi


def test_crossref_item_to_candidate_normalizes_doi_and_metadata():
    item = {
        "DOI": "https://doi.org/10.1103/PhysRevLett.124.048301",
        "title": ["Modeling Echo Chambers and Polarization Dynamics in Social Networks"],
        "issued": {"date-parts": [[2020, 1, 31]]},
        "author": [{"given": "Fabian", "family": "Baumann"}],
        "container-title": ["Physical Review Letters"],
        "publisher": "American Physical Society",
        "is-referenced-by-count": 200,
        "type": "journal-article",
        "URL": "https://doi.org/10.1103/PhysRevLett.124.048301",
    }
    candidate = doi.crossref_item_to_candidate(item)
    assert candidate["doi"] == "10.1103/PhysRevLett.124.048301"
    assert candidate["title"].startswith("Modeling Echo Chambers")
    assert candidate["year"] == 2020
    assert candidate["authors"] == ["Fabian Baumann"]
    assert candidate["metadata_sources"] == ["Crossref"]


def test_openalex_item_to_candidate_keeps_doi_less_arxiv_records():
    item = {
        "id": "https://openalex.org/W123",
        "doi": None,
        "ids": {"openalex": "https://openalex.org/W123"},
        "title": "Opinion dynamics: Statistical physics and beyond",
        "publication_year": 2025,
        "authorships": [{"author": {"display_name": "Michele Starnini"}}],
        "primary_location": {
            "landing_page_url": "https://arxiv.org/abs/2507.11521",
            "source": {"display_name": "arXiv", "host_organization_name": "arXiv"},
        },
        "cited_by_count": 0,
        "type": "article",
    }
    candidate = doi.openalex_item_to_candidate(item)
    assert candidate["doi"] is None
    assert candidate["arxiv_id"] == "2507.11521"
    assert candidate["openalex_id"] == "https://openalex.org/W123"
    assert candidate["metadata_sources"] == ["OpenAlex"]


def test_datacite_record_to_candidate_extracts_attributes():
    record = {
        "id": "10.48550/arXiv.2507.11521",
        "attributes": {
            "doi": "10.48550/arXiv.2507.11521",
            "titles": [{"title": "Opinion dynamics: Statistical physics and beyond"}],
            "publicationYear": 2025,
            "creators": [{"name": "Starnini, Michele"}],
            "publisher": "arXiv",
            "url": "https://arxiv.org/abs/2507.11521",
            "types": {"resourceTypeGeneral": "Preprint"},
            "citationCount": 3,
        },
    }
    candidate = doi.datacite_record_to_candidate(record)
    assert candidate["doi"] == "10.48550/arXiv.2507.11521"
    assert candidate["arxiv_id"] == "2507.11521"
    assert candidate["title"].startswith("Opinion dynamics")
    assert candidate["metadata_sources"] == ["DataCite"]


def test_arxiv_entry_to_candidate_parses_atom_entry():
    xml = """
    <entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <id>http://arxiv.org/abs/2507.11521v1</id>
      <title>Opinion dynamics: Statistical physics and beyond</title>
      <published>2025-07-15T00:00:00Z</published>
      <author><name>Michele Starnini</name></author>
      <link href="http://arxiv.org/abs/2507.11521v1" rel="alternate" />
      <arxiv:primary_category term="physics.soc-ph" />
    </entry>
    """
    entry = ET.fromstring(xml)
    candidate = doi.arxiv_entry_to_candidate(entry)
    assert candidate["arxiv_id"] == "2507.11521"
    assert candidate["year"] == 2025
    assert candidate["authors"] == ["Michele Starnini"]
    assert candidate["venue"] == "arXiv"
    assert candidate["arxiv_category"] == "physics.soc-ph"


def test_candidate_matching_strict_loose_and_all_fields():
    candidate = {
        "title": "Opinion dynamics: Statistical physics and beyond",
        "authors": ["Michele Starnini", "Fabian Baumann"],
        "year": 2025,
        "venue": "arXiv",
        "doi": None,
        "arxiv_id": "2507.11521",
        "openalex_id": "https://openalex.org/W123",
        "url": "https://arxiv.org/abs/2507.11521",
    }
    assert doi.candidate_matches(candidate, title="opinion dynamics", author="starnini", year="2025")
    assert not doi.candidate_matches(candidate, title="network science", author="starnini")
    assert doi.candidate_matches(candidate, title="dynamics beyond", allow_loose_title=True)
    assert doi.candidate_matches_loose_query(candidate, "starnini opinion dynamics")
