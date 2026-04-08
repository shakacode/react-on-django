from __future__ import annotations

from django import template

from ..component import render_react_component, render_react_component_hash

register = template.Library()
RENDER_CONTEXT_KEY = "react_on_django:context_emitted"


def _should_include_context_script(context) -> bool:
    include_context = not context.render_context.get(RENDER_CONTEXT_KEY, False)
    context.render_context[RENDER_CONTEXT_KEY] = True
    return include_context


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
