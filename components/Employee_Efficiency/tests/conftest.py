"""Isolate every test run from the component's operational SQLite database."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_test_db = Path(tempfile.gettempdir()) / f"employee_efficiency_tests_{os.getpid()}.db"
os.environ["DATABASE_PATH"] = str(_test_db)
