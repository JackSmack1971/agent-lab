#!/usr/bin/env python3
import json, sys, pathlib
from jsonschema import validate, Draft202012Validator
def main():
    if len(sys.argv) != 3:
        print("Usage: validate_json.py <data.json> <schema.json>", file=sys.stderr)
        sys.exit(2)
    data_p = pathlib.Path(sys.argv[1]); schema_p = pathlib.Path(sys.argv[2])
    data = json.loads(data_p.read_text(encoding="utf-8"))
    schema = json.loads(schema_p.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validate(instance=data, schema=schema)
    print(f"OK: {data_p} conforms to {schema_p}")
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
