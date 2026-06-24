"""Scholarly MEtadata Lookup Interface (smeli)."""
from __future__ import annotations

from . import bibtex, candidates, cli, http, normalize, sources
from .bibtex import *
from .candidates import *
from .cli import main
from .normalize import *
from .sources import *

__all__ = [
    *normalize.__all__,
    *candidates.__all__,
    *sources.__all__,
    *bibtex.__all__,
    "main",
]
