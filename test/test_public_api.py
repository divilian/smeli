import ast
from pathlib import Path

import smeli


PUBLIC_MODULES = [
    smeli.bibtex,
    smeli.candidates,
    smeli.cli,
    smeli.config,
    smeli.http,
    smeli.normalize,
    smeli.sources,
]


def _module_definitions(module):
    path = Path(module.__file__)
    tree = ast.parse(path.read_text())
    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    names.append(target.id)
    return names


def test_module_all_lists_only_public_existing_names():
    for module in PUBLIC_MODULES:
        assert hasattr(module, "__all__")
        for name in module.__all__:
            assert not name.startswith("_")
            assert hasattr(module, name)


def test_non_private_module_definitions_are_exported():
    for module in PUBLIC_MODULES:
        exported = set(module.__all__)
        for name in _module_definitions(module):
            if not name.startswith("_"):
                assert name in exported


def test_top_level_all_exposes_package_api_without_private_helpers():
    assert "get_paper_candidates" in smeli.__all__
    assert "get_metadata" in smeli.__all__
    assert "get_orcids" in smeli.__all__
    assert "search_orcids" in smeli.__all__
    assert "get_best_structured_metadata" not in smeli.__all__
    assert not hasattr(smeli, "get_best_structured_metadata")
    assert "clean_doi" in smeli.__all__
    assert "candidate_to_bibtex" in smeli.__all__
    assert "main" in smeli.__all__
    assert all(not name.startswith("_") for name in smeli.__all__)
    assert "_fetch_json" not in smeli.__all__
    assert "_crossref_item_to_candidate" not in smeli.__all__


def test_public_api_uses_paper_terminology_not_work_terminology():
    assert "get_paper_candidates" in smeli.__all__
    assert "get_work_candidates" not in smeli.__all__
    assert all("work_candidates" not in name for name in smeli.__all__)
    assert not hasattr(smeli, "get_work_candidates")
