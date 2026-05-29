"""Unit tests — app.core.utils"""

from app.core.utils import safe_json_load


def test_safe_json_load_none_returns_default():
    assert safe_json_load(None) is None


def test_safe_json_load_empty_string_returns_default():
    assert safe_json_load("") is None


def test_safe_json_load_valid_json_returns_parsed():
    assert safe_json_load('{"key": "val"}') == {"key": "val"}


def test_safe_json_load_invalid_json_returns_default():
    assert safe_json_load("not-json") is None


def test_safe_json_load_custom_default():
    assert safe_json_load("bad", default={"fallback": True}) == {"fallback": True}


def test_safe_json_load_type_error_returns_default():
    # json.loads raises TypeError for non-string/bytes — exercise that branch
    assert safe_json_load(123) is None  # type: ignore[arg-type]
