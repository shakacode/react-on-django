from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import get_language

from . import __version__
from .conf import get_react_on_django_settings
from .renderer.base import ComponentMarkup, ResolvedRenderOptions
from .renderer.client_renderer import ClientRenderer
from .utils.json_output import serialize_json

HTML_OPTION_KEYS = {
    "html_options",
    "id",
    "prerender",
    "trace",
    "replay_console",
    "raise_on_prerender_error",
    "random_dom_id",
}

DOM_ID_SEGMENT_RE = re.compile(r"[^A-Za-z0-9:_-]+")


class ReactOnDjangoError(Exception):
    """Base exception for React on Django rendering errors."""


def _sanitize_dom_id_segment(component_name: str) -> str:
    sanitized = DOM_ID_SEGMENT_RE.sub("-", component_name).strip("-")
    return sanitized or "component"


def _build_dom_id(component_name: str, *, explicit_id: str | None, random_dom_id: bool) -> str:
    if explicit_id:
        return explicit_id

    base_dom_id = f"{_sanitize_dom_id_segment(component_name)}-react-component"
    if random_dom_id:
        return f"{base_dom_id}-{uuid.uuid4()}"
    return base_dom_id


def _merge_html_options(
    html_options: Mapping[str, Any] | None,
    extra_html_attributes: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(html_options or {})
    merged.update(extra_html_attributes)
    return merged


def _build_page_context(request: HttpRequest | None) -> dict[str, Any]:
    language = get_language() or getattr(settings, "LANGUAGE_CODE", "en-us")
    href = request.build_absolute_uri() if request is not None else ""
    parsed = urlsplit(href)
    location = parsed.path
    if parsed.query:
        location = f"{location}?{parsed.query}"

    return {
        "componentRegistryTimeout": get_react_on_django_settings().component_registry_timeout,
        # The shared JS runtime still expects RailsContext-compatible keys.
        "railsEnv": "development" if getattr(settings, "DEBUG", False) else "production",
        "inMailer": False,
        "i18nLocale": language,
        "i18nDefaultLocale": getattr(settings, "LANGUAGE_CODE", "en-us"),
        "rorVersion": __version__,
        "rorPro": False,
        "href": href,
        "location": location,
        "scheme": parsed.scheme,
        "host": parsed.hostname or "",
        "port": parsed.port,
        "pathname": parsed.path,
        "search": parsed.query or None,
        "httpAcceptLanguage": request.META.get("HTTP_ACCEPT_LANGUAGE", "") if request else "",
        "serverSide": False,
    }


def _resolve_render_options(
    component_name: str,
    *,
    props: Any = None,
    request: HttpRequest | None = None,
    prerender: bool | None = None,
    html_options: Mapping[str, Any] | None = None,
    component_id: str | None = None,
    trace: bool | None = None,
    replay_console: bool | None = None,
    raise_on_prerender_error: bool | None = None,
    random_dom_id: bool | None = None,
    extra_html_attributes: Mapping[str, Any] | None = None,
) -> ResolvedRenderOptions:
    config = get_react_on_django_settings()
    effective_random_dom_id = config.random_dom_id if random_dom_id is None else random_dom_id
    props_json = serialize_json(props)
    return ResolvedRenderOptions(
        component_name=component_name,
        dom_id=_build_dom_id(
            component_name,
            explicit_id=component_id,
            random_dom_id=effective_random_dom_id,
        ),
        html_options=_merge_html_options(html_options, extra_html_attributes or {}),
        page_context=_build_page_context(request),
        prerender=config.prerender if prerender is None else prerender,
        props_json=props_json,
        trace=config.trace if trace is None else trace,
        replay_console=config.replay_console if replay_console is None else replay_console,
        raise_on_prerender_error=(
            config.raise_on_prerender_error
            if raise_on_prerender_error is None
            else raise_on_prerender_error
        ),
    )


def render_react_component(
    component_name: str,
    *,
    props: Any = None,
    request: HttpRequest | None = None,
    include_context_script: bool = True,
    **kwargs: Any,
) -> str:
    html_options = kwargs.pop("html_options", None)
    render_options = _resolve_render_options(
        component_name,
        props=props,
        request=request,
        prerender=kwargs.pop("prerender", None),
        html_options=html_options,
        component_id=kwargs.pop("id", None),
        trace=kwargs.pop("trace", None),
        replay_console=kwargs.pop("replay_console", None),
        raise_on_prerender_error=kwargs.pop("raise_on_prerender_error", None),
        random_dom_id=kwargs.pop("random_dom_id", None),
        extra_html_attributes=kwargs,
    )

    if render_options.prerender:
        raise ReactOnDjangoError(
            "Server-side rendering is not implemented yet. "
            "Set prerender=False to use client rendering."
        )

    rendered = ClientRenderer().render(
        render_options,
        include_context_script=include_context_script,
    )
    return rendered.markup


def render_react_component_hash(
    component_name: str,
    *,
    props: Any = None,
    request: HttpRequest | None = None,
    include_context_script: bool = True,
    **kwargs: Any,
) -> ComponentMarkup:
    html_options = kwargs.pop("html_options", None)
    render_options = _resolve_render_options(
        component_name,
        props=props,
        request=request,
        prerender=kwargs.pop("prerender", None),
        html_options=html_options,
        component_id=kwargs.pop("id", None),
        trace=kwargs.pop("trace", None),
        replay_console=kwargs.pop("replay_console", None),
        raise_on_prerender_error=kwargs.pop("raise_on_prerender_error", None),
        random_dom_id=kwargs.pop("random_dom_id", None),
        extra_html_attributes=kwargs,
    )

    if render_options.prerender:
        raise ReactOnDjangoError(
            "Server-side rendering is not implemented yet. "
            "Set prerender=False to use client rendering."
        )

    return ClientRenderer().render(render_options, include_context_script=include_context_script)
