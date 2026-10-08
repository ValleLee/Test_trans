from swepro_trans.validation.revision import _selector_is_emitted


def test_config_selector_does_not_count_as_emitted_test_code(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    selector = "test/units/example.py::TestExample::test_added_by_pr"
    (tests / "config.json").write_text(
        '{"pass_to_pass": ["' + selector + '"]}', encoding="utf-8"
    )
    (tests / "test.sh").write_text(
        "#!/bin/sh\npython3 parser.py --config config.json\n", encoding="utf-8"
    )
    (tests / "parser.py").write_text(
        "import json\njson.load(open('config.json'))\n", encoding="utf-8"
    )

    assert not _selector_is_emitted(selector, tests)


def test_test_source_in_bundle_counts_as_emitted(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_converted.py").write_text(
        "def test_behavior_added_by_conversion():\n    assert product_result() == expected\n",
        encoding="utf-8",
    )

    assert _selector_is_emitted(
        "test_converted.py::test_behavior_added_by_conversion", tests
    )
