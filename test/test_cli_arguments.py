import smeli.cli as cli


def test_infer_search_data_treats_doi_as_identifier():
    search = cli._infer_search_data_from_text("10.1126/science.1102081")
    assert search["identifier"] == "10.1126/science.1102081"
    assert search["query"] is None


def test_infer_search_data_extracts_arxiv_identifier_from_url():
    search = cli._infer_search_data_from_text("https://arxiv.org/abs/2507.11521v1")
    assert search["identifier"] == "2507.11521v1"
    assert search["query"] is None


def test_infer_search_data_extracts_openalex_identifier_from_url():
    search = cli._infer_search_data_from_text("https://openalex.org/W123456789")
    assert search["identifier"] == "W123456789"
    assert search["query"] is None


def test_infer_search_data_treats_non_identifier_text_as_broad_query():
    search = cli._infer_search_data_from_text("still building the memex davies")
    assert search["identifier"] is None
    assert search["title"] is None
    assert search["author"] is None
    assert search["query"] == "still building the memex davies"


def test_infer_search_data_extracts_year_from_free_form_query():
    search = cli._infer_search_data_from_text("still building the memex davies 1995")
    assert search["year"] == "1995"
    assert search["query"] == "still building the memex davies"


def test_one_shot_identifier_displays_single_match_without_choice(monkeypatch):
    calls = []

    def fake_get_paper_candidates(**kwargs):
        calls.append(kwargs)
        return [{"title": "A Paper", "doi": "10.1126/science.1102081"}]

    def fake_print_selected_paper_details(candidate, *, pause_at_end=True):
        calls.append({"selected": candidate, "pause_at_end": pause_at_end})

    monkeypatch.setattr(cli, "get_paper_candidates", fake_get_paper_candidates)
    monkeypatch.setattr(cli, "_print_selected_paper_details", fake_print_selected_paper_details)
    monkeypatch.setattr(cli, "_choose_from_results", lambda results, **kwargs: (_ for _ in ()).throw(AssertionError("should not ask user to choose")))

    cli._run_one_shot(["10.1126/science.1102081"])

    assert calls[0]["identifier"] == "10.1126/science.1102081"
    assert calls[1]["selected"]["title"] == "A Paper"
    assert calls[1]["pause_at_end"] is False


def test_one_shot_free_form_query_auto_selects_single_match(monkeypatch):
    calls = []

    def fake_get_paper_candidates(**kwargs):
        calls.append(kwargs)
        return [{"title": "Still Building the Memex", "authors": ["Stephen Davies"]}]

    def fake_print_selected_paper_details(candidate, *, pause_at_end=True):
        calls.append({"selected": candidate, "pause_at_end": pause_at_end})

    monkeypatch.setattr(cli, "get_paper_candidates", fake_get_paper_candidates)
    monkeypatch.setattr(cli, "_choose_from_results", lambda results, **kwargs: (_ for _ in ()).throw(AssertionError("should not ask user to choose")))
    monkeypatch.setattr(cli, "_print_selected_paper_details", fake_print_selected_paper_details)

    cli._run_one_shot(["still", "building", "the", "memex", "davies"])

    assert calls[0]["query"] == "still building the memex davies"
    assert calls[0]["identifier"] is None
    assert calls[1]["selected"]["title"] == "Still Building the Memex"
    assert calls[1]["pause_at_end"] is False


def test_one_shot_list_flag_forces_result_list_for_single_match(monkeypatch):
    calls = []

    def fake_get_paper_candidates(**kwargs):
        calls.append(kwargs)
        return [{"title": "Still Building the Memex", "authors": ["Stephen Davies"]}]

    monkeypatch.setattr(cli, "get_paper_candidates", fake_get_paper_candidates)
    monkeypatch.setattr(cli, "_choose_from_results", lambda results, **kwargs: calls.append({"results": results, **kwargs}))
    monkeypatch.setattr(cli, "_print_selected_paper_details", lambda candidate, **kwargs: (_ for _ in ()).throw(AssertionError("should not auto-select when --list is used")))

    cli._run_one_shot(["--list", "still", "building", "the", "memex", "davies"])

    assert calls[0]["query"] == "still building the memex davies"
    assert calls[1]["results"][0]["title"] == "Still Building the Memex"
    assert calls[1]["pause_at_end"] is False


def test_infer_search_data_extracts_orcid_identifier():
    search = cli._infer_search_data_from_text("https://orcid.org/0000-0002-0254-6627")
    assert search["identifier"] == "0000-0002-0254-6627"
    assert search["query"] is None


def test_one_shot_no_results_omits_search_data(monkeypatch, capsys):
    monkeypatch.setattr(cli, "get_paper_candidates", lambda **kwargs: [])

    cli._run_one_shot(["Stephen", "Davies", "University", "of", "Mary", "Washington"])

    output = capsys.readouterr().out
    assert "No paper candidates found matching those criteria." in output
    assert "Search data so far" not in output


def test_print_search_data_shows_identifier_type_for_doi_and_orcid(capsys):
    cli._print_search_data({"title": None, "author": None, "year": None, "identifier": "10.1126/science.1102081"})
    cli._print_search_data({"title": None, "author": None, "year": None, "identifier": "0000-0002-0254-6627"})

    output = capsys.readouterr().out
    assert "identifier (DOI):" in output
    assert "10.1126/science.1102081" in output
    assert "identifier (ORCID):" in output
    assert "0000-0002-0254-6627" in output


def test_serialize_candidate_colors_title_author_year_and_ids():
    output = cli._serialize_candidate({
        "title": "Still building the memex",
        "authors": ["Stephen Davies"],
        "year": 2011,
        "doi": "10.1145/1897816.1897840",
        "arxiv_id": None,
        "openalex_id": "https://openalex.org/W123",
        "metadata_sources": ["Crossref"],
    })

    assert cli._TITLE_COLOR in output
    assert cli._AUTHOR_COLOR in output
    assert cli._YEAR_COLOR in output
    assert cli._ID_COLOR in output
    assert "Still building the memex" in output
    assert "Stephen Davies" in output
    assert "2011" in output
    assert "10.1145/1897816.1897840" in output


def test_help_flag_prints_usage_without_lookup(monkeypatch, capsys):
    monkeypatch.setattr(cli, "get_paper_candidates", lambda **kwargs: (_ for _ in ()).throw(AssertionError("help should not run lookup")))

    cli.main(["-h"])

    output = capsys.readouterr().out
    assert "Usage:" in output
    assert "smeli [--list] <query-or-identifier>" in output
    assert "-h, --help" in output
    assert "Examples:" in output


def test_long_help_flag_prints_usage_without_lookup(monkeypatch, capsys):
    monkeypatch.setattr(cli, "get_paper_candidates", lambda **kwargs: (_ for _ in ()).throw(AssertionError("help should not run lookup")))

    cli._run_one_shot(["--help"])

    output = capsys.readouterr().out
    assert "Run Smeli with no arguments" in output
    assert "--list" in output


def test_parse_one_shot_fielded_long_options():
    search_data, force_list, direct_identifier = cli._parse_one_shot_args([
        "--author", "Stephen Davies",
        "--title", "Still building the memex",
        "--year", "1995",
    ])

    assert search_data["author"] == "Stephen Davies"
    assert search_data["title"] == "Still building the memex"
    assert search_data["year"] == "1995"
    assert search_data["identifier"] is None
    assert search_data["query"] is None
    assert force_list is False
    assert direct_identifier is False


def test_parse_one_shot_fielded_short_options_and_list():
    search_data, force_list, direct_identifier = cli._parse_one_shot_args([
        "--list", "-a", "Starnini", "-t", "opinion dynamics", "-y", "2025",
    ])

    assert search_data["author"] == "Starnini"
    assert search_data["title"] == "opinion dynamics"
    assert search_data["year"] == "2025"
    assert force_list is True
    assert direct_identifier is False


def test_parse_one_shot_identifier_option_takes_precedence():
    search_data, _, direct_identifier = cli._parse_one_shot_args([
        "--identifier", "10.1126/science.1102081",
        "--author", "Someone Else",
        "--title", "A Different Title",
    ])

    assert search_data["identifier"] == "10.1126/science.1102081"
    assert search_data["author"] == "Someone Else"
    assert search_data["title"] == "A Different Title"
    assert direct_identifier is True


def test_parse_one_shot_equals_forms():
    search_data, _, _ = cli._parse_one_shot_args([
        "--author=Stephen Davies",
        "--title=Still building the memex",
        "--year=1995",
    ])

    assert search_data["author"] == "Stephen Davies"
    assert search_data["title"] == "Still building the memex"
    assert search_data["year"] == "1995"


def test_one_shot_fielded_options_call_lookup(monkeypatch):
    calls = []

    def fake_get_paper_candidates(**kwargs):
        calls.append(kwargs)
        return [{"title": "Still Building the Memex", "authors": ["Stephen Davies"]}]

    def fake_print_selected_paper_details(candidate, *, pause_at_end=True):
        calls.append({"selected": candidate, "pause_at_end": pause_at_end})

    monkeypatch.setattr(cli, "get_paper_candidates", fake_get_paper_candidates)
    monkeypatch.setattr(cli, "_choose_from_results", lambda results, **kwargs: (_ for _ in ()).throw(AssertionError("should not ask user to choose")))
    monkeypatch.setattr(cli, "_print_selected_paper_details", fake_print_selected_paper_details)

    cli._run_one_shot(["--author", "Stephen Davies", "--title", "Still building the memex", "--year", "1995"])

    assert calls[0]["author"] == "Stephen Davies"
    assert calls[0]["title"] == "Still building the memex"
    assert calls[0]["year"] == "1995"
    assert calls[0]["query"] is None
    assert calls[1]["selected"]["title"] == "Still Building the Memex"
    assert calls[1]["pause_at_end"] is False
