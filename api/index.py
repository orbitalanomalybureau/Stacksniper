"""Vercel serverless entrypoint — re-exports the FastAPI application."""
import os
import sys

# Ensure Vercel uses in-memory SQLite (no persistent filesystem)
os.environ.setdefault("USE_SQLITE_MEMORY", "true")

# Add project root and backend directory to sys.path so imports resolve
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "backend"))

from backend.app.main import app  # noqa: E402
