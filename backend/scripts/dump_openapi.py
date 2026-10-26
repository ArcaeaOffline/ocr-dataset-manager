"""Write the app's OpenAPI schema to openapi.json at the workspace root.

The frontend generates its wire types from that file, and
`tests/test_openapi_spec.py` fails when the committed file drifts from
the app's current schema; rerun this script after API changes.
"""

import json
from pathlib import Path

from app.main import app

spec_path = Path(__file__).resolve().parents[2] / "openapi.json"
spec_path.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"wrote {spec_path}")
