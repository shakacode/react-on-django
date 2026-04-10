from __future__ import annotations

from collections.abc import Iterator

from ..conf import get_react_on_django_settings
from ..errors import ReactOnDjangoError
from ..server_rendering import (
    build_streaming_rendering_request,
    format_prerender_error,
    merge_client_props,
    resolve_renderer_bundle,
    stream_server_render,
)
from ..utils.html_output import (
    join_html_fragments,
    render_component_spec_script,
    render_console_replay_script,
    render_context_script,
    render_dom_container_end,
    render_dom_container_start,
)
from .base import BaseRenderer, ComponentMarkup, ResolvedRenderOptions


class StreamingRenderer(BaseRenderer):
    def stream(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> Iterator[str]:
        config = get_react_on_django_settings()
        bundle = resolve_renderer_bundle(config.server_bundle_js_file)
        rsc_bundle = (
            resolve_renderer_bundle(config.rsc_bundle_js_file)
            if config.react_client_manifest_file and config.react_server_client_manifest_file
            else None
        )
        dependency_bundles = (rsc_bundle,) if rsc_bundle is not None else ()
        stream_results = stream_server_render(
            rendering_request=build_streaming_rendering_request(
                component_name=options.component_name,
                dom_id=options.dom_id,
                props_json=options.props_json,
                page_context=options.page_context,
                trace=options.trace,
                rsc_bundle=rsc_bundle,
                registered_stores=options.registered_stores,
                store_dependencies=options.store_dependencies,
            ),
            bundle=bundle,
            dependency_bundles=dependency_bundles,
        )

        if include_context_script:
            yield render_context_script(options.page_context)
        yield render_dom_container_start(options.dom_id, html_options=options.html_options)

        saw_errors = False
        error_message = ""
        console_snippets: list[str] = []
        client_props = None
        for result in stream_results:
            if result.html:
                yield str(result.html)
            if result.console_replay_script:
                console_snippets.append(result.console_replay_script)
            if result.client_props is not None:
                client_props = result.client_props
            if result.has_errors:
                saw_errors = True
                error_message = format_prerender_error(result)

        yield render_dom_container_end(html_options=options.html_options)
        props_json = merge_client_props(options.props_json, client_props)
        yield render_component_spec_script(
            component_name=options.component_name,
            dom_id=options.dom_id,
            props_json=props_json,
            trace=options.trace,
            store_dependencies=options.store_dependencies,
            immediate_hydration=options.immediate_hydration,
        )
        if options.replay_console and console_snippets:
            yield render_console_replay_script("\n".join(console_snippets))

        if saw_errors and options.raise_on_prerender_error:
            raise ReactOnDjangoError(error_message)

    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        context_script = (
            render_context_script(options.page_context) if include_context_script else ""
        )
        config = get_react_on_django_settings()
        bundle = resolve_renderer_bundle(config.server_bundle_js_file)
        rsc_bundle = (
            resolve_renderer_bundle(config.rsc_bundle_js_file)
            if config.react_client_manifest_file and config.react_server_client_manifest_file
            else None
        )
        dependency_bundles = (rsc_bundle,) if rsc_bundle is not None else ()
        stream_results = stream_server_render(
            rendering_request=build_streaming_rendering_request(
                component_name=options.component_name,
                dom_id=options.dom_id,
                props_json=options.props_json,
                page_context=options.page_context,
                trace=options.trace,
                rsc_bundle=rsc_bundle,
                registered_stores=options.registered_stores,
                store_dependencies=options.store_dependencies,
            ),
            bundle=bundle,
            dependency_bundles=dependency_bundles,
        )

        html_chunks: list[str] = []
        console_snippets: list[str] = []
        error_message = ""
        saw_errors = False
        client_props = None
        for result in stream_results:
            if result.html:
                html_chunks.append(str(result.html))
            if result.console_replay_script:
                console_snippets.append(result.console_replay_script)
            if result.client_props is not None:
                client_props = result.client_props
            if result.has_errors:
                saw_errors = True
                error_message = format_prerender_error(result)

        if saw_errors and options.raise_on_prerender_error:
            raise ReactOnDjangoError(error_message)

        props_json = merge_client_props(options.props_json, client_props)
        container_html = join_html_fragments(
            render_dom_container_start(options.dom_id, html_options=options.html_options),
            "".join(html_chunks),
            render_dom_container_end(html_options=options.html_options),
        )
        component_script = render_component_spec_script(
            component_name=options.component_name,
            dom_id=options.dom_id,
            props_json=props_json,
            trace=options.trace,
            store_dependencies=options.store_dependencies,
            immediate_hydration=options.immediate_hydration,
        )
        console_script = (
            render_console_replay_script("\n".join(console_snippets))
            if options.replay_console and console_snippets
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
        )
