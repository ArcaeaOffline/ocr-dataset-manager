import json
from pathlib import Path

from app.main import app

SPEC_PATH = Path(__file__).resolve().parents[2] / "openapi.json"


def test_committed_openapi_spec_matches_current_schema():
    committed = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert committed == app.openapi(), (
        "openapi.json is stale; regenerate it with backend/scripts/dump_openapi.py"
    )
