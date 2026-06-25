"""Scholarly MEtadata Lookup Interface (smeli).

The top-level package re-exports Smeli's public library API from the
``normalize``, ``candidates``, ``sources``, and ``bibtex`` modules, plus the
CLI entrypoint ``main``. Names not listed in ``smeli.__all__`` are internal
implementation details and may change without notice.
"""
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
