"""The committed openapi.json is the client contract (web and mobile generate types from it).

If this fails after an intended API change, run `make openapi` and commit the result. CI separately
fails on *breaking* changes against the base branch (oasdiff).
"""

import json
from pathlib import Path

from app.core.config import Settings
from app.main import create_app

SNAPSHOT = Path(__file__).resolve().parents[2] / "openapi.json"


def test_openapi_matches_committed_snapshot() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    current = json.loads(json.dumps(app.openapi(), sort_keys=True))
    committed = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert current == committed, "openapi.json is stale: run `make openapi` and commit it"


def test_health_routes_public_and_metrics_hidden() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    paths = app.openapi()["paths"]
    assert "/healthz" in paths
    assert "/readyz" in paths
    assert "/metrics" not in paths  # internal only
