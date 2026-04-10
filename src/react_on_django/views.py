from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest, HttpResponseBadRequest, StreamingHttpResponse

from .component import _resolve_render_options
from .renderer.rsc_renderer import RSCRenderer
from .renderer.streaming_renderer import StreamingRenderer
from .server_rendering import RSC_PAYLOAD_CONTENT_TYPE
from .utils.streaming_output import streaming_content_for_request


def stream_react_component_response(
    request: HttpRequest,
    component_name: str,
    *,
    props: Any = None,
    content_type: str = "text/html; charset=utf-8",
    **kwargs: Any,
) -> StreamingHttpResponse:
    options = _resolve_render_options(
        component_name,
        props=props,
        request=request,
        prerender=True,
        html_options=kwargs.pop("html_options", None),
        component_id=kwargs.pop("id", None),
        server_render_method=kwargs.pop("server_render_method", None),
        trace=kwargs.pop("trace", None),
        replay_console=kwargs.pop("replay_console", None),
        raise_on_prerender_error=kwargs.pop("raise_on_prerender_error", None),
        random_dom_id=kwargs.pop("random_dom_id", None),
        extra_html_attributes=kwargs,
    )
    return StreamingHttpResponse(
        streaming_content_for_request(
            request,
            StreamingRenderer().stream(options, include_context_script=True),
        ),
        content_type=content_type,
    )


def rsc_payload_response(
    request: HttpRequest,
    component_name: str,
    *,
    props: Any = None,
    content_type: str = RSC_PAYLOAD_CONTENT_TYPE,
    **kwargs: Any,
) -> StreamingHttpResponse:
    options = _resolve_render_options(
        component_name,
        props=props,
        request=request,
        prerender=True,
        html_options=kwargs.pop("html_options", None),
        component_id=kwargs.pop("id", None),
        server_render_method="rsc",
        trace=kwargs.pop("trace", None),
        replay_console=False,
        raise_on_prerender_error=kwargs.pop("raise_on_prerender_error", None),
        random_dom_id=kwargs.pop("random_dom_id", None),
        extra_html_attributes=kwargs,
    )
    response = StreamingHttpResponse(
        streaming_content_for_request(request, RSCRenderer().stream_payload(options)),
        content_type=content_type,
    )
    response["Content-Type"] = content_type
    return response


def rsc_payload_view(request: HttpRequest, component_name: str):
    props = _load_request_props(request)
    if isinstance(props, HttpResponseBadRequest):
        return props
    return rsc_payload_response(request, component_name, props=props)


def _load_request_props(request: HttpRequest) -> Any | HttpResponseBadRequest:
    if request.method == "GET":
        props = request.GET.get("props")
        if props is None:
            return {}
        try:
            return json.loads(props)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Expected a JSON object in the 'props' query parameter.")

    raw_body = request.body.decode("utf-8").strip()
    if not raw_body:
        return {}

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Expected a JSON request body.")
