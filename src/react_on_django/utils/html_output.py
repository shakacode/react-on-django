from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from django.forms.utils import flatatt
from django.utils.html import conditional_escape
from django.utils.safestring import SafeData, mark_safe

from .json_output import serialize_json

COMPONENT_SCRIPT_CLASS = "js-react-on-rails-component"
CONTEXT_SCRIPT_ID = "js-react-on-rails-context"
STORE_SCRIPT_ATTRIBUTE = "data-js-react-on-rails-store"
ATTRIBUTION_COMMENT = "<!-- Powered by React on Django (c) ShakaCode -->"
TAG_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9:-]*$")


def _normalize_tag_name(tag_name: str) -> str:
    if not TAG_NAME_RE.match(tag_name):
        raise ValueError(f"Invalid HTML tag name: {tag_name}")
    return tag_name


def _safe_body(body: str) -> str:
    if isinstance(body, SafeData):
        return str(body)
    return str(conditional_escape(body))


def join_html_fragments(*fragments: str) -> str:
    content = "\n".join(fragment for fragment in fragments if fragment)
    return mark_safe(content)


def render_dom_container(
    dom_id: str,
    html_options: Mapping[str, Any] | None = None,
    body: str = "",
) -> str:
    return mark_safe(
        f"{render_dom_container_start(dom_id, html_options=html_options)}"
        f"{_safe_body(body)}"
        f"{render_dom_container_end(html_options=html_options)}"
    )


def render_dom_container_start(
    dom_id: str,
    html_options: Mapping[str, Any] | None = None,
) -> str:
    attributes = dict(html_options or {})
    tag_name = _normalize_tag_name(str(attributes.pop("tag", "div")))
    attributes["id"] = dom_id
    return mark_safe(f"<{tag_name}{flatatt(attributes)}>")


def render_dom_container_end(
    html_options: Mapping[str, Any] | None = None,
) -> str:
    tag_name = _normalize_tag_name(str(dict(html_options or {}).get("tag", "div")))
    return mark_safe(f"</{tag_name}>")


def render_json_script(
    json_content: str,
    *,
    element_id: str | None = None,
    css_class: str | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> str:
    attrs = dict(attributes or {})
    if element_id is not None:
        attrs["id"] = element_id
    if css_class is not None:
        attrs["class"] = css_class
    attrs["type"] = "application/json"
    return mark_safe(f"<script{flatatt(attrs)}>{json_content}</script>")


def render_component_spec_script(
    *,
    component_name: str,
    dom_id: str,
    props_json: str,
    trace: bool,
    store_dependencies: tuple[str, ...] | None = None,
    immediate_hydration: bool | None = None,
) -> str:
    attributes = {
        "data-component-name": component_name,
        "data-dom-id": dom_id,
        "data-trace": "true" if trace else None,
        "data-store-dependencies": (
            json.dumps(list(store_dependencies), separators=(",", ":"))
            if store_dependencies
            else None
        ),
        "data-immediate-hydration": "true" if immediate_hydration else None,
    }
    spec_tag = render_json_script(
        props_json,
        element_id=f"js-react-on-rails-component-{dom_id}",
        css_class=COMPONENT_SCRIPT_CLASS,
        attributes=attributes,
    )
    if not immediate_hydration:
        return spec_tag

    return join_html_fragments(
        spec_tag,
        render_inline_script(
            "typeof ReactOnRails === 'object' && "
            f"ReactOnRails.reactOnRailsComponentLoaded({json.dumps(dom_id)});"
        ),
    )


def render_store_hydration_script(
    *,
    store_name: str,
    props_json: str,
    immediate_hydration: bool | None = None,
) -> str:
    spec_tag = render_json_script(
        props_json,
        attributes={
            STORE_SCRIPT_ATTRIBUTE: store_name,
            "data-immediate-hydration": "true" if immediate_hydration else None,
        },
    )
    if not immediate_hydration:
        return spec_tag

    return join_html_fragments(
        spec_tag,
        render_inline_script(
            "typeof ReactOnRails === 'object' && "
            f"ReactOnRails.reactOnRailsStoreLoaded({json.dumps(store_name)});"
        ),
    )


def render_context_script(context_data: Mapping[str, Any]) -> str:
    return join_html_fragments(
        mark_safe(ATTRIBUTION_COMMENT),
        render_json_script(serialize_json(dict(context_data)), element_id=CONTEXT_SCRIPT_ID),
    )


def render_external_script_tag(
    src: str,
    *,
    defer: bool = True,
    async_attr: bool = False,
    attributes: Mapping[str, Any] | None = None,
) -> str:
    attrs = dict(attributes or {})
    attrs["src"] = src
    if defer:
        attrs["defer"] = True
    if async_attr:
        attrs["async"] = True
    return mark_safe(f"<script{flatatt(attrs)}></script>")


def render_stylesheet_tag(
    href: str,
    *,
    attributes: Mapping[str, Any] | None = None,
) -> str:
    attrs = {"rel": "stylesheet", "href": href}
    attrs.update(attributes or {})
    return mark_safe(f"<link{flatatt(attrs)} />")


def render_inline_script(
    body: str,
    *,
    element_id: str | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> str:
    attrs = dict(attributes or {})
    if element_id is not None:
        attrs["id"] = element_id
    safe_body = str(body) if isinstance(body, SafeData) else body
    return mark_safe(f"<script{flatatt(attrs)}>{safe_body}</script>")


def render_console_replay_script(script_body: str) -> str:
    if not script_body:
        return ""
    return render_inline_script(mark_safe(script_body), element_id="consoleReplayLog")
