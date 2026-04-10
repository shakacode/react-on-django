from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import get_language

from . import __version__
from .assets import render_generated_component_assets, render_generated_store_assets
from .conf import get_react_on_django_settings
from .errors import ReactOnDjangoError
from .middleware import (
    get_current_request,
    get_registered_store_names,
    get_registered_stores,
    pop_deferred_stores,
    register_store,
    should_emit_context_script,
)
from .renderer.base import RegisteredStore, ResolvedRenderOptions
from .renderer.client_renderer import ClientRenderer
from .renderer.rsc_renderer import RSCRenderer
from .renderer.server_renderer import ServerRenderer
from .renderer.streaming_renderer import StreamingRenderer
from .server_rendering import (
    COMPONENT_HTML_KEY,
    build_js_evaluation_request,
    format_prerender_error,
    perform_server_render,
    resolve_renderer_bundle,
)
from .utils.html_output import (
    join_html_fragments,
    render_console_replay_script,
    render_context_script,
    render_store_hydration_script,
)
from .utils.json_output import serialize_json

HTML_OPTION_KEYS = {
    "html_options",
    "id",
    "prerender",
    "server_render_method",
    "trace",
    "replay_console",
    "raise_on_prerender_error",
    "random_dom_id",
}

DOM_ID_SEGMENT_RE = re.compile(r"[^A-Za-z0-9:_-]+")

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
    merged = _normalize_html_attributes(html_options)
    merged.update(_normalize_html_attributes(extra_html_attributes))
    return merged


def _normalize_html_attribute_name(name: str) -> str:
    if name.endswith("_"):
        name = name[:-1]
    return name.replace("_", "-")


def _normalize_html_attributes(attributes: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for raw_key, value in (attributes or {}).items():
        if value is None:
            continue

        key = _normalize_html_attribute_name(str(raw_key))
        if key in {"data", "aria"} and isinstance(value, Mapping):
            for nested_key, nested_value in value.items():
                if nested_value is None:
                    continue
                nested_name = _normalize_html_attribute_name(str(nested_key))
                normalized[f"{key}-{nested_name}"] = nested_value
            continue

        normalized[key] = value
    return normalized


def _build_page_context(
    request: HttpRequest | None,
    *,
    server_render_method: str,
) -> dict[str, Any]:
    config = get_react_on_django_settings()
    language = get_language() or getattr(settings, "LANGUAGE_CODE", "en-us")
    href = request.build_absolute_uri() if request is not None else ""
    parsed = urlsplit(href)
    location = parsed.path
    if parsed.query:
        location = f"{location}?{parsed.query}"

    return {
        "componentRegistryTimeout": config.component_registry_timeout,
        # The shared JS runtime still expects RailsContext-compatible keys.
        "railsEnv": "development" if getattr(settings, "DEBUG", False) else "production",
        "inMailer": False,
        "i18nLocale": language,
        "i18nDefaultLocale": getattr(settings, "LANGUAGE_CODE", "en-us"),
        "rorVersion": __version__,
        "rorPro": config.ror_pro,
        "rorProVersion": config.ror_pro_version,
        "href": href,
        "location": location,
        "scheme": parsed.scheme,
        "host": parsed.hostname or "",
        "port": parsed.port,
        "pathname": parsed.path,
        "search": parsed.query or None,
        "httpAcceptLanguage": request.META.get("HTTP_ACCEPT_LANGUAGE", "") if request else "",
        "rscPayloadGenerationUrlPath": (
            config.rsc_payload_generation_url_path
            if (
                server_render_method == "rsc"
                or (
                    config.react_client_manifest_file
                    and config.react_server_client_manifest_file
                )
            )
            else None
        ),
        "serverSide": False,
    }


def rails_context(
    request: HttpRequest | None = None,
    *,
    server_side: bool = True,
    server_render_method: str | None = None,
) -> dict[str, Any]:
    config = get_react_on_django_settings()
    effective_server_render_method = (
        config.server_render_method if server_render_method is None else server_render_method
    )
    context = _build_page_context(
        request or get_current_request(),
        server_render_method=effective_server_render_method,
    )
    context["serverSide"] = server_side
    return context


def render_rails_context(
    request: HttpRequest | None = None,
    *,
    server_render_method: str | None = None,
) -> str:
    return render_context_script(
        rails_context(
            request,
            server_side=False,
            server_render_method=server_render_method,
        )
    )


def _generated_pack_loading_options() -> tuple[bool, bool]:
    strategy = get_react_on_django_settings().generated_component_packs_loading_strategy
    return (strategy != "async", strategy == "async")


def _generated_component_assets_html(component_name: str) -> str:
    defer, async_attr = _generated_pack_loading_options()
    return render_generated_component_assets(
        component_name,
        defer=defer,
        async_attr=async_attr,
    )


def _generated_store_assets_html(store_name: str) -> str:
    defer, async_attr = _generated_pack_loading_options()
    return render_generated_store_assets(
        store_name,
        defer=defer,
        async_attr=async_attr,
    )


def _coerce_store_dependencies(store_dependencies: Any) -> tuple[str, ...] | None:
    if store_dependencies is None:
        names = get_registered_store_names()
        return names or None
    if isinstance(store_dependencies, str):
        return (store_dependencies,)
    dependencies = tuple(dict.fromkeys(str(name) for name in store_dependencies))
    return dependencies or None


def _renderer_for_options(options: ResolvedRenderOptions):
    if not options.prerender:
        return ClientRenderer()

    if options.server_render_method == "streaming":
        return StreamingRenderer()
    if options.server_render_method == "rsc":
        return RSCRenderer()
    return ServerRenderer()


def _resolve_render_options(
    component_name: str,
    *,
    props: Any = None,
    request: HttpRequest | None = None,
    prerender: bool | None = None,
    html_options: Mapping[str, Any] | None = None,
    component_id: str | None = None,
    server_render_method: str | None = None,
    trace: bool | None = None,
    replay_console: bool | None = None,
    raise_on_prerender_error: bool | None = None,
    random_dom_id: bool | None = None,
    store_dependencies: Any = None,
    immediate_hydration: bool | None = None,
    auto_load_bundle: bool | None = None,
    extra_html_attributes: Mapping[str, Any] | None = None,
) -> ResolvedRenderOptions:
    config = get_react_on_django_settings()
    active_request = request or get_current_request()
    effective_random_dom_id = config.random_dom_id if random_dom_id is None else random_dom_id
    effective_server_render_method = (
        config.server_render_method if server_render_method is None else server_render_method
    )
    props_json = serialize_json(props)
    return ResolvedRenderOptions(
        component_name=component_name,
        dom_id=_build_dom_id(
            component_name,
            explicit_id=component_id,
            random_dom_id=effective_random_dom_id,
        ),
        html_options=_merge_html_options(html_options, extra_html_attributes or {}),
        page_context=_build_page_context(
            active_request,
            server_render_method=effective_server_render_method,
        ),
        prerender=config.prerender if prerender is None else prerender,
        props_json=props_json,
        trace=config.trace if trace is None else trace,
        replay_console=config.replay_console if replay_console is None else replay_console,
        raise_on_prerender_error=(
            config.raise_on_prerender_error
            if raise_on_prerender_error is None
            else raise_on_prerender_error
        ),
        server_render_method=effective_server_render_method,
        store_dependencies=_coerce_store_dependencies(store_dependencies),
        immediate_hydration=immediate_hydration,
        auto_load_bundle=config.auto_load_bundle if auto_load_bundle is None else auto_load_bundle,
        registered_stores=get_registered_stores(),
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
        server_render_method=kwargs.pop("server_render_method", None),
        trace=kwargs.pop("trace", None),
        replay_console=kwargs.pop("replay_console", None),
        raise_on_prerender_error=kwargs.pop("raise_on_prerender_error", None),
        random_dom_id=kwargs.pop("random_dom_id", None),
        store_dependencies=kwargs.pop("store_dependencies", None),
        immediate_hydration=kwargs.pop("immediate_hydration", None),
        auto_load_bundle=kwargs.pop("auto_load_bundle", None),
        extra_html_attributes=kwargs,
    )
    include_context_script = include_context_script and should_emit_context_script()

    renderer = _renderer_for_options(render_options)
    rendered = renderer.render(
        render_options,
        include_context_script=include_context_script,
    )
    if not render_options.auto_load_bundle:
        return rendered.markup
    return join_html_fragments(
        _generated_component_assets_html(render_options.component_name),
        rendered.markup,
    )


def render_react_component_hash(
    component_name: str,
    *,
    props: Any = None,
    request: HttpRequest | None = None,
    include_context_script: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    html_options = kwargs.pop("html_options", None)
    render_options = _resolve_render_options(
        component_name,
        props=props,
        request=request,
        prerender=True,
        html_options=html_options,
        component_id=kwargs.pop("id", None),
        server_render_method=kwargs.pop("server_render_method", None),
        trace=kwargs.pop("trace", None),
        replay_console=kwargs.pop("replay_console", None),
        raise_on_prerender_error=kwargs.pop("raise_on_prerender_error", None),
        random_dom_id=kwargs.pop("random_dom_id", None),
        store_dependencies=kwargs.pop("store_dependencies", None),
        immediate_hydration=kwargs.pop("immediate_hydration", None),
        auto_load_bundle=kwargs.pop("auto_load_bundle", None),
        extra_html_attributes=kwargs,
    )
    include_context_script = include_context_script and should_emit_context_script()

    renderer = _renderer_for_options(render_options)
    rendered = renderer.render(render_options, include_context_script=include_context_script)
    if not rendered.extra:
        raise ReactOnDjangoError(
            "Render function used by react_component_hash is expected to return an object. "
            "Use render_react_component for string HTML results."
        )
    assets_html = (
        _generated_component_assets_html(render_options.component_name)
        if render_options.auto_load_bundle
        else ""
    )
    markup = join_html_fragments(assets_html, rendered.markup)
    result = {
        COMPONENT_HTML_KEY: markup,
        "html": rendered.html,
        "script": rendered.script,
        "markup": markup,
        "assets": assets_html,
        "dom_id": rendered.dom_id,
        "component_name": rendered.component_name,
        "props_json": rendered.props_json,
    }
    if rendered.extra:
        result.update(rendered.extra)
    return result


def redux_store(
    store_name: str,
    *,
    props: Any = None,
    request: HttpRequest | None = None,
    defer: bool = False,
    immediate_hydration: bool | None = None,
    auto_load_bundle: bool | None = None,
) -> str:
    config = get_react_on_django_settings()
    active_request = request or get_current_request()
    resolved_auto_load_bundle = (
        config.auto_load_bundle if auto_load_bundle is None else auto_load_bundle
    )
    store = RegisteredStore(
        name=store_name,
        props_json=serialize_json(props),
        immediate_hydration=immediate_hydration,
    )
    register_store(store, defer=defer)
    if defer:
        return ""

    context_script = (
        render_rails_context(active_request) if should_emit_context_script() else ""
    )
    assets_html = _generated_store_assets_html(store_name) if resolved_auto_load_bundle else ""
    store_markup = render_store_hydration_script(
        store_name=store.name,
        props_json=store.props_json,
        immediate_hydration=store.immediate_hydration,
    )
    return join_html_fragments(assets_html, context_script, store_markup)


def redux_store_hydration_data(request: HttpRequest | None = None) -> str:
    deferred_stores = pop_deferred_stores()
    if not deferred_stores:
        return ""

    active_request = request or get_current_request()
    config = get_react_on_django_settings()
    fragments: list[str] = []
    if should_emit_context_script():
        fragments.append(render_rails_context(active_request))
    if config.auto_load_bundle:
        rendered_assets: set[str] = set()
        for store in deferred_stores:
            if store.name in rendered_assets:
                continue
            fragments.append(_generated_store_assets_html(store.name))
            rendered_assets.add(store.name)
    for store in deferred_stores:
        fragments.append(
            render_store_hydration_script(
                store_name=store.name,
                props_json=store.props_json,
                immediate_hydration=store.immediate_hydration,
            )
        )
    return join_html_fragments(*fragments)


def server_render_js(
    js_expression: str,
    *,
    request: HttpRequest | None = None,
    replay_console: bool | None = None,
    raise_on_prerender_error: bool | None = None,
    throw_js_errors: bool = False,
) -> str:
    config = get_react_on_django_settings()
    effective_replay_console = (
        config.replay_console if replay_console is None else replay_console
    )
    effective_raise = (
        config.raise_on_prerender_error
        if raise_on_prerender_error is None
        else raise_on_prerender_error
    )
    result = perform_server_render(
        rendering_request=build_js_evaluation_request(
            js_expression=js_expression,
            page_context=rails_context(request or get_current_request(), server_side=True),
            throw_js_errors=throw_js_errors,
        ),
        bundle=resolve_renderer_bundle(config.server_bundle_js_file),
    )
    if result.has_errors and effective_raise:
        raise ReactOnDjangoError(format_prerender_error(result))

    console_script = (
        render_console_replay_script(result.console_replay_script)
        if effective_replay_console
        else ""
    )
    return join_html_fragments(mark_safe(str(result.html or "")), console_script)
