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
    assert config.bundle_name == "application"
    assert config.prerender is False
    assert config.trace is True
    assert config.auto_load_bundle is False
    assert config.generated_component_packs_loading_strategy == "defer"
    assert config.replay_console is True
    assert config.server_renderer_pool_size == 4
    assert config.rendering_server_url == "http://localhost:3500"
    assert config.renderer_protocol_version == "2.0.0"
    assert config.ror_pro is False
    assert config.react_client_manifest_file is None
    assert config.react_server_client_manifest_file is None
    assert config.json_encoder is ReactOnDjangoJSONEncoder


def test_configuration_overrides(settings):
    settings.REACT_ON_DJANGO = {
        "prerender": True,
        "trace": False,
        "bundle_name": "admin",
        "server_renderer_pool_size": 2,
        "rendering_server_url": "https://renderer.example.com",
        "random_dom_id": False,
        "auto_load_bundle": True,
        "generated_component_packs_loading_strategy": "async",
        "ror_pro": True,
        "ror_pro_version": "16.5.1",
        "react_client_manifest_file": "packs/react-client-manifest.json",
        "react_server_client_manifest_file": "packs/react-server-client-manifest.json",
    }
    reload_react_on_django_settings()

    config = get_react_on_django_settings()

    assert config.bundle_name == "admin"
    assert config.prerender is True
    assert config.trace is False
    assert config.auto_load_bundle is True
    assert config.generated_component_packs_loading_strategy == "async"
    assert config.server_renderer_pool_size == 2
    assert config.rendering_server_url == "https://renderer.example.com"
    assert config.random_dom_id is False
    assert config.ror_pro is True
    assert config.ror_pro_version == "16.5.1"
    assert config.react_client_manifest_file == "packs/react-client-manifest.json"
    assert config.react_server_client_manifest_file == "packs/react-server-client-manifest.json"


def test_configuration_rejects_invalid_rendering_server_url(settings):
    settings.REACT_ON_DJANGO = {"rendering_server_url": "/relative"}
    reload_react_on_django_settings()

    with pytest.raises(ImproperlyConfigured):
        get_react_on_django_settings()


def test_configuration_requires_both_rsc_manifest_files(settings):
    settings.REACT_ON_DJANGO = {
        "react_client_manifest_file": "packs/react-client-manifest.json",
    }
    reload_react_on_django_settings()

    with pytest.raises(ImproperlyConfigured):
        get_react_on_django_settings()


def test_configuration_rejects_invalid_generated_pack_loading_strategy(settings):
    settings.REACT_ON_DJANGO = {"generated_component_packs_loading_strategy": "eager"}
    reload_react_on_django_settings()

    with pytest.raises(ImproperlyConfigured):
        get_react_on_django_settings()
