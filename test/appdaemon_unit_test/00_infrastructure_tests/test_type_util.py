from __future__ import annotations

from unit_helpers.type_util import extract_from_dictionary, repeat_item


def test_extract_existing_item_from_dictionary() -> None:
    d = {"key1": "value1", "key2": "value2"}
    result = extract_from_dictionary(d, "key1")
    assert result == "value1"
    assert d == {"key2": "value2"}


def test_extract_nonexisting_item_from_dictionary() -> None:
    d = {"key1": "value1", "key2": "value2"}
    result = extract_from_dictionary(d, "key3")
    assert result is None
    assert d == {"key1": "value1", "key2": "value2"}


def test_repeat_item() -> None:
    result = repeat_item("foobar", 3)
    assert result == ["foobar", "foobar", "foobar"]