from __future__ import annotations

from react_on_django.conf import reload_react_on_django_settings
from react_on_django.utils.json_output import (
    ReactOnDjangoJSONEncoder,
    escape_json_string,
    json_safe_and_pretty,
    sanitized_props_string,
    serialize_json,
)


def test_escape_json_string_escapes_script_sensitive_characters():
    value = '{"special":"<>&\u2028\u2029"}'

    assert escape_json_string(value) == '{"special":"\\u003c\\u003e\\u0026\\u2028\\u2029"}'


def test_serialize_json_accepts_existing_json_string():
    value = '{"name":"Ada","x":"</script><script>alert(1)</script>"}'
    expected = (
        '{"name":"Ada","x":"\\u003c/script\\u003e\\u003cscript\\u003e'
        "alert(1)\\u003c/script\\u003e\"}"
    )

    assert serialize_json(value) == expected


def test_serialize_json_uses_custom_serialization_hook(settings):
    class Example:
        def __init__(self, value: str) -> None:
            self.value = value

    def serialization_hook(value):
        if isinstance(value, Example):
            return {"value": value.value}
        raise TypeError

    settings.REACT_ON_DJANGO = {
        "serialization_hook": serialization_hook,
        "json_encoder": ReactOnDjangoJSONEncoder,
    }
    reload_react_on_django_settings()

    assert serialize_json({"example": Example("Ada")}) == '{"example":{"value":"Ada"}}'


def test_sanitized_props_string_accepts_hashes_and_json_strings():
    assert sanitized_props_string({"name": "Ada"}) == '{"name":"Ada"}'
    assert (
        sanitized_props_string('{"name":"Ada","x":"</script>"}')
        == '{"name":"Ada","x":"\\u003c/script\\u003e"}'
    )


def test_json_safe_and_pretty_handles_none_string_and_mapping():
    assert json_safe_and_pretty(None) == "{}"
    assert json_safe_and_pretty({"name": "Ada"}) == '{"name":"Ada"}'
    assert json_safe_and_pretty('{"name":"</script>"}') == '{"name":"\\u003c/script\\u003e"}'
