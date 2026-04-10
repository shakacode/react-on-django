from __future__ import annotations

from ..utils.html_output import (
    join_html_fragments,
    render_component_spec_script,
    render_context_script,
    render_dom_container,
)
from .base import BaseRenderer, ComponentMarkup, ResolvedRenderOptions


class ClientRenderer(BaseRenderer):
    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        container_html = render_dom_container(
            dom_id=options.dom_id,
            html_options=options.html_options,
        )
        component_script = render_component_spec_script(
            component_name=options.component_name,
            dom_id=options.dom_id,
            props_json=options.props_json,
            trace=options.trace,
            store_dependencies=options.store_dependencies,
            immediate_hydration=options.immediate_hydration,
        )
        context_script = (
            render_context_script(options.page_context) if include_context_script else ""
        )
        markup = join_html_fragments(context_script, container_html, component_script)
        script = join_html_fragments(context_script, component_script)
        return ComponentMarkup(
            html=container_html,
            script=script,
            markup=markup,
            dom_id=options.dom_id,
            component_name=options.component_name,
            props_json=options.props_json,
        )
