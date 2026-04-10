from __future__ import annotations

from django.utils.safestring import mark_safe

from ..conf import get_react_on_django_settings
from ..errors import ReactOnDjangoError
from ..server_rendering import (
    build_ssr_rendering_request,
    coerce_rendered_html,
    format_prerender_error,
    merge_client_props,
    perform_server_render,
    resolve_renderer_bundle,
)
from ..utils.html_output import (
    join_html_fragments,
    render_component_spec_script,
    render_console_replay_script,
    render_context_script,
    render_dom_container,
)
from .base import BaseRenderer, ComponentMarkup, ResolvedRenderOptions


class ServerRenderer(BaseRenderer):
    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        result = perform_server_render(
            rendering_request=build_ssr_rendering_request(
                component_name=options.component_name,
                dom_id=options.dom_id,
                props_json=options.props_json,
                page_context=options.page_context,
                trace=options.trace,
                registered_stores=options.registered_stores,
                store_dependencies=options.store_dependencies,
            ),
            bundle=resolve_renderer_bundle(get_react_on_django_settings().server_bundle_js_file),
        )

        if result.has_errors and options.raise_on_prerender_error:
            raise ReactOnDjangoError(format_prerender_error(result))

        component_html, extra = coerce_rendered_html(result.html)
        props_json = merge_client_props(options.props_json, result.client_props)

        container_html = render_dom_container(
            dom_id=options.dom_id,
            html_options=options.html_options,
            body=mark_safe(component_html),
        )
        component_script = render_component_spec_script(
            component_name=options.component_name,
            dom_id=options.dom_id,
            props_json=props_json,
            trace=options.trace,
            store_dependencies=options.store_dependencies,
            immediate_hydration=options.immediate_hydration,
        )
        context_script = (
            render_context_script(options.page_context) if include_context_script else ""
        )
        console_script = (
            render_console_replay_script(result.console_replay_script)
            if options.replay_console
            else ""
        )
        markup = join_html_fragments(
            context_script,
            container_html,
            component_script,
            console_script,
        )
        script = join_html_fragments(context_script, component_script, console_script)
        return ComponentMarkup(
            html=container_html,
            script=script,
            markup=markup,
            dom_id=options.dom_id,
            component_name=options.component_name,
            props_json=props_json,
            extra=extra or None,
        )
