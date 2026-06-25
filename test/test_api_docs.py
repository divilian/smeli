import inspect
from pathlib import Path

import smeli


PUBLIC_MODULES = [
    smeli,
    smeli.bibtex,
    smeli.candidates,
    smeli.cli,
    smeli.normalize,
    smeli.sources,
]

REFERENCE_PAGES = {
    "smeli": Path("docs/reference/smeli.md"),
    "smeli.bibtex": Path("docs/reference/bibtex.md"),
    "smeli.candidates": Path("docs/reference/candidates.md"),
    "smeli.cli": Path("docs/reference/cli.md"),
    "smeli.normalize": Path("docs/reference/normalize.md"),
    "smeli.sources": Path("docs/reference/sources.md"),
}


DOCSTRING_SECTIONS = ("Args:", "Returns:", "Notes:", "Examples:")


def test_public_api_objects_have_useful_docstrings():
    for module in PUBLIC_MODULES:
        for name in module.__all__:
            obj = getattr(module, name)
            doc = inspect.getdoc(obj) or ""
            assert len(doc) >= 40, f"{module.__name__}.{name} needs a useful docstring"
            if inspect.isfunction(obj):
                assert any(section in doc for section in DOCSTRING_SECTIONS), (
                    f"{module.__name__}.{name} docstring should document arguments, "
                    "return value, notes, or examples"
                )


def test_reference_pages_cover_public_api():
    for module in PUBLIC_MODULES:
        page = REFERENCE_PAGES[module.__name__]
        assert page.exists(), f"missing reference page for {module.__name__}"
        text = page.read_text()
        assert f"::: {module.__name__}" in text
        for name in module.__all__:
            assert f"        - {name}" in text, f"{name} missing from {page}"


def test_return_docstrings_use_single_typed_google_style_item():
    for module in PUBLIC_MODULES:
        for name in module.__all__:
            obj = getattr(module, name)
            if not inspect.isfunction(obj):
                continue
            doc = inspect.getdoc(obj) or ""
            if "Returns:" not in doc:
                continue
            returns = doc.split("Returns:", 1)[1]
            next_section_positions = [
                returns.find(section)
                for section in DOCSTRING_SECTIONS
                if section != "Returns:" and returns.find(section) != -1
            ]
            if next_section_positions:
                returns = returns[: min(next_section_positions)]
            first_line = next(
                (line.strip() for line in returns.splitlines() if line.strip()),
                "",
            )
            assert ":" in first_line, (
                f"{module.__name__}.{name} Returns section should start with "
                "one typed Google-style return item, such as 'str: ...'"
            )
