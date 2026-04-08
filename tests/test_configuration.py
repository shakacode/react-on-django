from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured

from react_on_django.conf import get_react_on_django_settings, reload_react_on_django_settings
from react_on_django.utils.json_output import ReactOnDjangoJSONEncoder


def test_configuration_defaults(settings):
    settings.DEBUG = True
    settings.REACT_ON_DJANGO = {}
    reload_react_on_django_settings()

    config = get_react_on_django_settings()

    assert config.server_bundle_js_file == "server-bundle.js"
    assert config.prerender is False
    assert config.trace is True
    assert config.replay_console is True
    assert config.server_renderer_pool_size == 4
    assert config.rendering_server_url == "http://localhost:3500"
    assert config.json_encoder is ReactOnDjangoJSONEncoder


def test_configuration_overrides(settings):
    settings.REACT_ON_DJANGO = {
        "prerender": True,
        "trace": False,
        "server_renderer_pool_size": 2,
        "rendering_server_url": "https://renderer.example.com",
        "random_dom_id": False,
    }
    reload_react_on_django_settings()

    config = get_react_on_django_settings()

    assert config.prerender is True
    assert config.trace is False
    assert config.server_renderer_pool_size == 2
    assert config.rendering_server_url == "https://renderer.example.com"
    assert config.random_dom_id is False


def test_configuration_rejects_invalid_rendering_server_url(settings):
    settings.REACT_ON_DJANGO = {"rendering_server_url": "/relative"}
    reload_react_on_django_settings()

    with pytest.raises(ImproperlyConfigured):
        get_react_on_django_settings()
