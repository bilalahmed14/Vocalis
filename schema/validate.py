# /// script
# requires-python = ">=3.12"
# dependencies = ["jsonschema>=4.23"]
# ///
"""Check that the agent schema is valid JSON Schema and every example config matches it.

Usage: uv run schema/validate.py [config.json ...]
With no arguments, validates everything in examples/.
"""

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "agent.v1.schema.json"


def main(paths: list[str]) -> int:
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    configs = [Path(p) for p in paths] or sorted((ROOT / "examples").glob("*.json"))
    failed = 0
    for path in configs:
        errors = list(validator.iter_errors(json.loads(path.read_text())))
        if errors:
            failed += 1
            print(f"FAIL {path}")
            for error in errors:
                location = "/".join(str(part) for part in error.absolute_path) or "<root>"
                print(f"  {location}: {error.message}")
        else:
            print(f"ok   {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
