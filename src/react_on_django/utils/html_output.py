from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from django.forms.utils import flatatt
from django.utils.html import conditional_escape
from django.utils.safestring import SafeData, mark_safe

from .json_output import serialize_json

COMPONENT_SCRIPT_CLASS = "js-react-on-rails-component"
CONTEXT_SCRIPT_ID = "js-react-on-rails-context"
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
    attributes = dict(html_options or {})
    tag_name = _normalize_tag_name(str(attributes.pop("tag", "div")))
    attributes["id"] = dom_id
    return mark_safe(f"<{tag_name}{flatatt(attributes)}>{_safe_body(body)}</{tag_name}>")


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
) -> str:
    attributes = {
        "data-component-name": component_name,
        "data-dom-id": dom_id,
        "data-trace": "true" if trace else None,
    }
    return render_json_script(
        props_json,
        element_id=f"js-react-on-rails-component-{dom_id}",
        css_class=COMPONENT_SCRIPT_CLASS,
        attributes=attributes,
    )


def render_context_script(context_data: Mapping[str, Any]) -> str:
    return join_html_fragments(
        mark_safe(ATTRIBUTION_COMMENT),
        render_json_script(serialize_json(dict(context_data)), element_id=CONTEXT_SCRIPT_ID),
    )
