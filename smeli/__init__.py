"""Scholarly MEtadata Lookup Interface (smeli)."""
from __future__ import annotations

import requests as requests

from .normalize import *
from .candidates import *
from .sources import *
from .bibtex import *
from .http import *
from .cli import main
