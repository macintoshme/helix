"""Pytest configuration.

Points the app at a throwaway SQLite file and puts the `backend/` directory on
sys.path so the `app` namespace package is importable. This module is imported by
pytest before any test module, so the env var is set before `app.db` (which builds
its engine at import time) is ever imported.
"""
import os
import pathlib
import sys
import tempfile

_BACKEND = pathlib.Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Must be set before `app.db` / `app.main` are imported.
os.environ["MR_DB_PATH"] = str(
    pathlib.Path(tempfile.mkdtemp(prefix="helix-test-")) / "test.db"
)
os.environ.setdefault("HELIX_LOG_LEVEL", "WARNING")
os.environ.setdefault("HELIX_YTDLP_AUTO_UPDATE", "false")
