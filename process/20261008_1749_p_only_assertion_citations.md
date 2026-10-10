# P-only assertion citation gate

Date: 2026-10-08 17:49 CST

## Evidence

Navidrome `instance_navidrome__navidrome-23bebe4e06124becf1000e88472ae71a6ca7de4c`, `attempt_001/rev_009`, passed Base/Gold, behavior-role review, and positive QA, but its negative QA ended `rejected_negative_qa`. Candidate `negative_003` changed only `Content-Type` from JSON to `text/plain`; the JSON body and status remained unchanged. The negative Judge returned `EQUIVALENT` because P-only does not fix MIME type. The functional verifier rejected the candidate on its Content-Type assertion.

The converter self-review claimed Requirements/Interface only helped discover the public report contract, but it asserted that a non-JSON Content-Type must fail. That test assertion has no exact support in `source/problem_statement.md` or an approved addendum.

## Classification and scope

This is a general early-review gap: the converter and semantic Judge did not make the source-to-assertion entailment explicit for every executable assertion. It is not a request to add a MIME-type exception for Navidrome. The independent-audit standard remains unchanged.

## General fix

Updated the converter, focused-converter, and semantic-Judge prompts to require an assertion-to-contract table: every emitted assertion must cite exact P/addendum wording or an independently documented pre-existing public contract, and must be challenged with a P-conforming counterfactual. Construction evidence cannot supply normative force; broad capability-discovery language does not fix transport metadata or serialization format.

## Retry and verification

Navidrome was appended to `task_list/stage2_retry_queue_20261008.txt` and to the follow-up one-worker retry file after the already queued ProtonMail retry. Its current attempt remains preserved as rejected and is not qualified. The new prompt rules were checked in the active `configs/experiment.yaml` paths (`prompts/converter.md`, `prompts/judges/semantic.md`); focused prompt was kept consistent. The retry must pass pipeline gates and the same external audit standard before qualification.

## Follow-up: NodeBB artifact rejection

At 2026-10-08 17:55 CST, `instance_NodeBB__NodeBB-0c81642997ea1d827dbd02c311db9d4976112cd4-vf2cf3cbd463b7ad942381f1c6d077626485a1e9` attempt_001/rev_009 ended `rejected_artifact` after 8 repairs. The artifact contract reports that the rewrite row for `TestPostQueueMerge` references `test/converter_post_queue_merge.js`, which is absent from the emitted suite. This is an instance artifact/mapping failure, not evidence for a shared framework change. The ID is appended after Navidrome in the existing follow-up queue. A fresh retry must produce the referenced test and pass the ordinary gates plus external audit.

## Follow-up: OpenLibrary hard-replay rejection

At 2026-10-08 17:57 CST, `instance_internetarchive__openlibrary-09865f5fb549694d969f0a8e49b9d204ef1853ca-ve8c8d62a2b60610a3c4631f5f23ed866bada9818` attempt_008/rev_009 ended `rejected_hard` after 8 repairs. Artifact and semantic gates passed, but Gold replay failed one emitted selector: `test_to_markdown_roundtrip_preserves_authors` requires `title == ""`, while Gold parses the serialized empty title as `None`; 20 other selectors passed. The test's empty-state representation may exceed P's lossless/reproducible behavior contract. The attempt is preserved and queued for a fresh retry after the existing follow-up items; the retry must retain metadata behavior and pass Gold replay before external audit.


## Follow-up: repeated emitted-test mapping failures

At 2026-10-08, three more selected-100 attempts reached `rejected_artifact` after the converter's repair limit because a preserved F2P row named a converted selector whose source was absent from the submitted verifier:

- `instance_element-hq__element-web-494d9de6f0a94ffb491e74744d2735bce02dc0ab-vnan`, attempt_001/rev_009: rows referenced absent `test/verifier/RoomViewStore.verifier-test.ts` and `test/verifier/RoomView.verifier-test.tsx`.
- `instance_protonmail__webclients-6f8916fbadf1d1f4a26640f53b5cf7f55e8bedb7`, attempt_001/rev_009: a row referenced absent `src/app/store/_shares/useDefaultShare.converted.test.tsx`.
- `instance_NodeBB__NodeBB-0c81642997ea1d827dbd02c311db9d4976112cd4-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e`, attempt_001/rev_009: `TestPostQueueMerge` referenced absent `test/converter_post_queue_merge.js`.

These are repeated manifestations of one generic pre-submit artifact check gap: the trace/config can claim a selector without the converter verifying the complete chain from config selector to shipped or harness-generated source, runner collection, and a behavior-bearing assertion. Added this end-to-end selector/source/behavior audit to `prompts/converter.md` and `prompts/converter_focused.md`. The retry prompt must make the converter verify each link before spending semantic or Docker replay rounds. The existing artifact contract remains the hard backstop; no task-specific selector exception was added.

A related artifact failure, `instance_NodeBB__NodeBB-0e07f3c9bace416cbab078a30eae972868c0a8a3-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e` attempt_001/rev_009, had an incomplete `self_review.md` without the required terminal `SELF_REVIEW: PASS` marker. It is queued for a fresh attempt; this is a deterministic submission checklist item rather than a semantic finding.

All four new cases were added to the selected-100 retry queue. A current-state audit confirms all ten selected-100 `needs_review` tasks are assigned to either the active retry batch or its queued follow-up; none is added to the qualified list without framework completion and external audit PASS.

Additional confirmation: `instance_NodeBB__NodeBB-0f788b8eaa4bba3c142d171fd941d015c53b65fc-v0ec6d6c2baf3cb4797482ce4829bc25cd5716649` attempt_001/rev_009 ended `rejected_artifact` because eight F2P rows referenced the absent `test/_verifier_thumbs_converted.js`. It has been added to the selected-100 follow-up retry list. This reinforces the same selector/source integrity gap; no NodeBB-specific rule was added.

## Follow-up: NodeBB retained-P2P Gold replay errors

At 2026-10-08 10:21 UTC, `instance_NodeBB__NodeBB-05f2236193f407cf8e2072757fbd6bb170bc13f0-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e` attempt_001/rev_009 passed the artifact contract and semantic review but ended `rejected_hard`. The converted oldest-reply selector failed Base as expected and passed Gold. However, two original P2P selectors (`Topic's .fork should update the user's bookmark` and `Topic's teasers should return empty array`) were reported `ERROR` in both Base and Gold, so the complete Gold suite did not pass. The selectors remain in `pass_to_pass`; they were not excluded. Runner stderr was empty and Mocha's serialized `err` objects were empty, so the precise cause is not yet established. The task is queued for a fresh retry to diagnose and retain these P2P tests; do not classify it as qualified until Base/Gold replay and external audit pass.

## Follow-up: suite-level historical F2P under-conversion

During the selected-100 retry of `instance_tutao__tutanota-f3ffe17af6e8ab007e8d461355057ad237846d9d-vbc0d9ba8f0071fbe982809910959a6ff8884dbbf`, `attempt_002/rev_004` was rejected by semantic review because the converter dropped all obligations from suite-level `EntropyFacadeTest` and `LoginFacadeTest` selectors. Review found multiple product outcomes hidden behind facade/collaborator assertions: external storage effects, login/leader guards, and error recovery. It correctly rejected freezing the Gold facade methods, exact threshold/time constants, and log prefixes, but the converter dropped the product behavior with those implementation details.

This is a generic source-inspection gap: suite-level selectors can summarize many independently observable test cases, and a collaborator spy can encode either a replaceable internal call shape or a real external product effect. Updated `prompts/converter.md`, `prompts/converter_focused.md`, and `prompts/judges/semantic.md` to require case-level decomposition before classification, preservation of external effects/guards/recovery through a stable public boundary, and conversion of Base-existing behavior as regressions. No Tutanota-specific requirement was added. The current attempt remains in its framework repair loop and is not qualified; it must pass all gates and the standard external audit.

## Follow-up: suite-level drop repeated after semantic feedback

At 2026-10-08 10:52 UTC, Tutanota `attempt_002/rev_008` again classified the whole `EntropyFacadeTest` and `LoginFacadeTest` suites as `implementation_detail`/`drop`, with empty emitted selectors, despite the rev_007 semantic feedback enumerating product outcomes to preserve and the existing converter rule requiring source-case inspection. The rev_008 converter was still running when recorded; no final gate result is inferred here.

The prompt already contained the semantic principle, but it did not require a verifiable per-case inventory artifact before a suite-wide drop. Promoted this to a mandatory `self_review.md` mapping (source case/assertion → behavior vs mechanism → P/Base status → disposition → emitted selector or case-specific exclusion evidence) at the top-level converter decision and in the semantic Judge's opening checks. The external Judge must reject a suite-wide drop when that inventory is absent/incomplete or an excluded mechanism still has an independent Base-observable outcome. This is a generic evidence/ordering improvement; no Tutanota behavior or API was added to the prompt. `git diff --check -- prompts/converter.md prompts/judges/semantic.md` passes.

The current attempt remains under framework review. If it fails, retry under the updated prompt and do not qualify it until all historical F2P rows have functional mappings, the final instruction is P-only, P2P is retained, and the standard independent audit passes.
