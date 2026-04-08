from __future__ import annotations

import json
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder

from ..conf import get_react_on_django_settings

JSON_ESCAPE_TABLE = str.maketrans(
    {
        "<": "\\u003c",
        ">": "\\u003e",
        "&": "\\u0026",
        "\u2028": "\\u2028",
        "\u2029": "\\u2029",
    }
)


class ReactOnDjangoJSONEncoder(DjangoJSONEncoder):
    def default(self, obj: Any) -> Any:
        config = get_react_on_django_settings()

        if config.serialization_hook is not None:
            try:
                return config.serialization_hook(obj)
            except TypeError:
                pass

        serializer = getattr(obj, "react_on_django_serialize", None)
        if callable(serializer):
            return serializer()

        return super().default(obj)


def escape_json_string(value: str) -> str:
    return value.translate(JSON_ESCAPE_TABLE)


def serialize_json(value: Any, *, encoder: type[DjangoJSONEncoder] | None = None) -> str:
    if value is None:
        return "{}"

    if isinstance(value, str):
        return escape_json_string(value)

    encoder_class = encoder or get_react_on_django_settings().json_encoder
    raw_json = json.dumps(value, cls=encoder_class, separators=(",", ":"))
    return escape_json_string(raw_json)
