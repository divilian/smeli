import smeli


def test_author_name_extractors():
    crossref_item = {"author": [{"given": "Michele", "family": "Starnini"}, {"family": "Porter"}]}
    assert smeli.candidates._author_names_from_crossref(crossref_item) == ["Michele Starnini", "Porter"]

    openalex_item = {"authorships": [{"author": {"display_name": "Michele Starnini"}}]}
    assert smeli.candidates._author_names_from_openalex(openalex_item) == ["Michele Starnini"]

    datacite_attrs = {"creators": [{"name": "Starnini, Michele"}, {"givenName": "Mason", "familyName": "Porter"}]}
    assert smeli.candidates._author_names_from_datacite(datacite_attrs) == ["Starnini, Michele", "Mason Porter"]


def test_author_overlap_uses_lastish_name():
    assert smeli.normalize._author_overlap(["Michele Starnini"], ["Starnini, Michele"])
    assert smeli.normalize._author_overlap(["M. Porter"], ["Mason A. Porter"])
    assert not smeli.normalize._author_overlap(["Michele Starnini"], ["Jane Doe"])


def test_year_helpers():
    assert smeli.normalize._get_year_from_crossref({"published-online": {"date-parts": [[2025, 7, 15]]}}) == 2025
    assert smeli.normalize._get_year_from_crossref({"issued": {"date-parts": [[2020]]}}) == 2020
    assert smeli.normalize._get_year_from_date("2025-07-15T12:34:56Z") == 2025
    assert smeli.normalize._get_year_from_date("no year here") is None
    assert smeli.normalize._maybe_int("42") == 42
    assert smeli.normalize._maybe_int("not-int") is None
