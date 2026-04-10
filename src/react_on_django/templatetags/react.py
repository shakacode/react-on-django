from __future__ import annotations

from django import template

from ..assets import render_react_component_assets
from ..component import (
    redux_store,
    redux_store_hydration_data,
    render_rails_context,
    render_react_component,
    render_react_component_hash,
    server_render_js,
)

register = template.Library()
RENDER_CONTEXT_KEY = "react_on_django:context_emitted"


def _should_include_context_script(context) -> bool:
    include_context = not context.render_context.get(RENDER_CONTEXT_KEY, False)
    context.render_context[RENDER_CONTEXT_KEY] = True
    return include_context


@register.simple_tag
def react_component_assets(bundle_name=None, **kwargs):
    async_attr = kwargs.pop("async", False)
    return render_react_component_assets(
        bundle_name=bundle_name,
        async_attr=async_attr,
        **kwargs,
    )


@register.simple_tag(takes_context=True)
def react_context(context, **kwargs):
    if not _should_include_context_script(context):
        return ""
    return render_rails_context(
        request=context.get("request"),
        server_render_method=kwargs.get("server_render_method"),
    )


@register.simple_tag(takes_context=True)
def react_component(context, component_name, props=None, **kwargs):
    return render_react_component(
        component_name,
        props=props,
        request=context.get("request"),
        include_context_script=_should_include_context_script(context),
        **kwargs,
    )


@register.simple_tag(takes_context=True)
def react_component_hash(context, component_name, props=None, **kwargs):
    return render_react_component_hash(
        component_name,
        props=props,
        request=context.get("request"),
        include_context_script=_should_include_context_script(context),
        **kwargs,
    )


@register.simple_tag(takes_context=True)
def react_redux_store(context, store_name, props=None, **kwargs):
    return redux_store(
        store_name,
        props=props,
        request=context.get("request"),
        **kwargs,
    )


@register.simple_tag(takes_context=True)
def react_redux_store_hydration_data(context):
    return redux_store_hydration_data(request=context.get("request"))


@register.simple_tag(takes_context=True)
def react_server_render_js(context, js_expression, **kwargs):
    return server_render_js(
        js_expression,
        request=context.get("request"),
        **kwargs,
    )
