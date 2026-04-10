from __future__ import annotations

import json
from collections.abc import Iterator

from ..conf import get_react_on_django_settings
from ..errors import ReactOnDjangoError
from ..server_rendering import (
    build_rsc_rendering_request,
    format_prerender_error,
    resolve_renderer_bundle,
    stream_server_render,
)
from .base import BaseRenderer, ComponentMarkup, ResolvedRenderOptions


class RSCRenderer(BaseRenderer):
    def stream_payload(
        self,
        options: ResolvedRenderOptions,
    ) -> Iterator[str]:
        config = get_react_on_django_settings()
        rsc_bundle = resolve_renderer_bundle(config.rsc_bundle_js_file)
        dependencies = [resolve_renderer_bundle(config.server_bundle_js_file)]
        saw_errors = False
        error_message = ""

        for result in stream_server_render(
            rendering_request=build_rsc_rendering_request(
                component_name=options.component_name,
                dom_id=options.dom_id,
                props_json=options.props_json,
                page_context=options.page_context,
                trace=options.trace,
                rsc_bundle=rsc_bundle,
                registered_stores=options.registered_stores,
                store_dependencies=options.store_dependencies,
            ),
            bundle=rsc_bundle,
            dependency_bundles=dependencies,
        ):
            yield (
                json.dumps(
                    {
                        "html": str(result.html or ""),
                        "consoleReplayScript": result.console_replay_script,
                        "hasErrors": result.has_errors,
                        "renderingError": result.rendering_error,
                        "isShellReady": result.is_shell_ready,
                    }
                )
                + "\n"
            )
            if result.has_errors:
                saw_errors = True
                error_message = format_prerender_error(result)

        if saw_errors and options.raise_on_prerender_error:
            raise ReactOnDjangoError(error_message)

    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        payload = "".join(self.stream_payload(options))
        return ComponentMarkup(
            html=payload,
            script="",
            markup=payload,
            dom_id=options.dom_id,
            component_name=options.component_name,
            props_json=options.props_json,
        )
