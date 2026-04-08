from __future__ import annotations

from .conf import get_react_on_django_settings


def react_on_django(_request):
    return {"react_on_django": get_react_on_django_settings()}
