"""Print the OpenAPI document: `python -m app.scripts.dump_openapi > openapi.json`.

Builds the app without starting its lifespan, so no database or Redis is needed.
"""

import json
import sys

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
