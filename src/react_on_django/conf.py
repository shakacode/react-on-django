from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.core.signals import setting_changed
from django.dispatch import receiver

SerializerHook = Callable[[Any], Any]

DEFAULT_COMPONENT_REGISTRY_TIMEOUT = 5000
DEFAULT_RENDERING_SERVER_URL = "http://localhost:3500"
DEFAULT_SERVER_BUNDLE_JS_FILE = "server-bundle.js"
DEFAULT_SERVER_RENDERER_POOL_SIZE = 4
DEFAULT_RSC_BUNDLE_JS_FILE = "rsc-bundle.js"
DEFAULT_RENDERER_PROTOCOL_VERSION = "2.0.0"
DEFAULT_RSC_PAYLOAD_GENERATION_URL_PATH = "/react_on_django/rsc/"


@dataclass(frozen=True, slots=True)
class ReactOnDjangoSettings:
    bundle_name: str
    server_bundle_js_file: str
    prerender: bool
    trace: bool
    auto_load_bundle: bool
    generated_component_packs_loading_strategy: str
    replay_console: bool
    server_renderer_pool_size: int
    raise_on_prerender_error: bool
    node_modules_location: str
    server_render_method: str
    build_test_command: str
    rendering_server_url: str
    rendering_server_password: str
    rendering_server_timeout: float
    renderer_protocol_version: str
    random_dom_id: bool
    component_registry_timeout: int
    rsc_bundle_js_file: str
    rsc_payload_generation_url_path: str
    ror_pro: bool
    ror_pro_version: str | None
    react_client_manifest_file: str | None
    react_server_client_manifest_file: str | None
    json_encoder: type[DjangoJSONEncoder]
    serialization_hook: SerializerHook | None


def _default_settings() -> dict[str, Any]:
    from .utils.json_output import ReactOnDjangoJSONEncoder

    debug = bool(getattr(settings, "DEBUG", False))
    return {
        "bundle_name": "application",
        "server_bundle_js_file": DEFAULT_SERVER_BUNDLE_JS_FILE,
        "prerender": False,
        "trace": debug,
        "auto_load_bundle": False,
        "generated_component_packs_loading_strategy": "defer",
        "replay_console": True,
        "server_renderer_pool_size": DEFAULT_SERVER_RENDERER_POOL_SIZE,
        "raise_on_prerender_error": debug,
        "node_modules_location": "",
        "server_render_method": "",
        "build_test_command": "npm run build:test",
        "rendering_server_url": DEFAULT_RENDERING_SERVER_URL,
        "rendering_server_password": "",
        "rendering_server_timeout": 10.0,
        "renderer_protocol_version": DEFAULT_RENDERER_PROTOCOL_VERSION,
        "random_dom_id": True,
        "component_registry_timeout": DEFAULT_COMPONENT_REGISTRY_TIMEOUT,
        "rsc_bundle_js_file": DEFAULT_RSC_BUNDLE_JS_FILE,
        "rsc_payload_generation_url_path": DEFAULT_RSC_PAYLOAD_GENERATION_URL_PATH,
        "ror_pro": False,
        "ror_pro_version": None,
        "react_client_manifest_file": None,
        "react_server_client_manifest_file": None,
        "json_encoder": ReactOnDjangoJSONEncoder,
        "serialization_hook": None,
    }


def _validate_settings(config: dict[str, Any]) -> None:
    if (
        not isinstance(config["server_renderer_pool_size"], int)
        or config["server_renderer_pool_size"] < 1
    ):
        raise ImproperlyConfigured(
            "REACT_ON_DJANGO.server_renderer_pool_size must be a positive integer."
        )

    if (
        not isinstance(config["component_registry_timeout"], int)
        or config["component_registry_timeout"] < 0
    ):
        raise ImproperlyConfigured(
            "REACT_ON_DJANGO.component_registry_timeout must be zero or greater."
        )

    timeout = config["rendering_server_timeout"]
    if not isinstance(timeout, int | float) or timeout <= 0:
        raise ImproperlyConfigured(
            "REACT_ON_DJANGO.rendering_server_timeout must be greater than zero."
        )

    encoder = config["json_encoder"]
    if not isinstance(encoder, type) or not issubclass(encoder, DjangoJSONEncoder):
        raise ImproperlyConfigured("REACT_ON_DJANGO.json_encoder must subclass DjangoJSONEncoder.")

    rendering_server_url = config["rendering_server_url"]
    parsed = urlsplit(rendering_server_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ImproperlyConfigured(
            "REACT_ON_DJANGO.rendering_server_url must be an absolute http or https URL."
        )

    if not isinstance(config["renderer_protocol_version"], str) or not config[
        "renderer_protocol_version"
    ].strip():
        raise ImproperlyConfigured(
            "REACT_ON_DJANGO.renderer_protocol_version must be a non-empty string."
        )

    if config["generated_component_packs_loading_strategy"] not in {"defer", "async"}:
        raise ImproperlyConfigured(
            "REACT_ON_DJANGO.generated_component_packs_loading_strategy must be "
            "'defer' or 'async'."
        )

    manifest_fields = (
        "react_client_manifest_file",
        "react_server_client_manifest_file",
    )
    provided_manifest_fields = [field for field in manifest_fields if config.get(field)]
    if provided_manifest_fields and len(provided_manifest_fields) != len(manifest_fields):
        raise ImproperlyConfigured(
            "REACT_ON_DJANGO.react_client_manifest_file and "
            "REACT_ON_DJANGO.react_server_client_manifest_file must be configured together."
        )


@lru_cache(maxsize=1)
def get_react_on_django_settings() -> ReactOnDjangoSettings:
    config = _default_settings()
    config.update(getattr(settings, "REACT_ON_DJANGO", {}))
    _validate_settings(config)
    return ReactOnDjangoSettings(**config)


def reload_react_on_django_settings() -> None:
    get_react_on_django_settings.cache_clear()


@receiver(setting_changed)
def _reload_settings(*, setting: str, **_: Any) -> None:
    if setting == "REACT_ON_DJANGO":
        reload_react_on_django_settings()
