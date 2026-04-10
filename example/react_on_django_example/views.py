from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from react_on_django.component import (
    _resolve_render_options,
    redux_store,
    render_react_component_hash,
)
from react_on_django.renderer.streaming_renderer import StreamingRenderer
from react_on_django.utils.streaming_output import streaming_content_for_request

XSS_NOTE = '<script>window.alert("xss-from-props")</script>'
PROPS_NAME = "Mr. Client Side Rendering"


def _example_context() -> dict[str, Any]:
    app_props_server_render = {
        "helloWorldData": {
            "name": PROPS_NAME,
            "note": XSS_NOTE,
        }
    }
    app_props_hello = {
        "helloWorldData": {
            "name": "Mrs. Client Side Rendering",
            "note": XSS_NOTE,
        }
    }
    app_props_hello_again = {
        "helloWorldData": {
            "name": "Mrs. Client Side Hello Again",
            "note": "A second component instance with different props.",
        }
    }
    rsc_props = {
        "name": "RSC from Django",
        "note": "The initial payload was embedded during server rendering.",
    }
    return {
        "app_props_server_render": app_props_server_render,
        "app_props_server_render_json": json.dumps(app_props_server_render, separators=(",", ":")),
        "app_props_hello": app_props_hello,
        "app_props_hello_again": app_props_hello_again,
        "store_component_props": {"storeName": "helloWorldStore"},
        "rsc_props": rsc_props,
        "hello_world_html_options": {
            "class": "my-hello-world-class",
            "data": {"x": 1, "y": 2},
        },
    }


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "index.html", _example_context())


def client_side_hello_world(request: HttpRequest) -> HttpResponse:
    return render(request, "client_side_hello_world.html", _example_context())


def client_side_hello_world_shared_store(request: HttpRequest) -> HttpResponse:
    return render(request, "client_side_hello_world_shared_store.html", _example_context())


def server_side_hello_world_shared_store(request: HttpRequest) -> HttpResponse:
    redux_store(
        "helloWorldStore",
        props=_example_context()["app_props_server_render"],
        request=request,
        defer=True,
    )
    return render(request, "server_side_hello_world_shared_store.html", _example_context())


def server_side_hello_world(request: HttpRequest) -> HttpResponse:
    return render(request, "server_side_hello_world.html", _example_context())


def _streaming_shell_response(
    request: HttpRequest,
    *,
    template_name: str,
    component_name: str,
    props: dict[str, Any],
    dom_id: str,
    server_render_method: str | None = None,
) -> StreamingHttpResponse:
    context = _example_context()
    shell = render_to_string(template_name, context, request=request)
    prefix, suffix = shell.split("<!--STREAM_COMPONENT-->", maxsplit=1)
    render_options = _resolve_render_options(
        component_name,
        props=props,
        request=request,
        prerender=True,
        html_options=None,
        component_id=dom_id,
        trace=True,
        server_render_method=server_render_method,
        replay_console=None,
        raise_on_prerender_error=None,
        random_dom_id=None,
        extra_html_attributes={},
    )
    component_stream = StreamingRenderer().stream(render_options, include_context_script=True)

    def iterator() -> Iterator[str]:
        yield prefix
        yield from component_stream
        yield suffix

    return StreamingHttpResponse(
        streaming_content_for_request(request, iterator()),
        content_type="text/html; charset=utf-8",
    )


def streaming_hello_world(request: HttpRequest) -> StreamingHttpResponse:
    return _streaming_shell_response(
        request,
        template_name="streaming_hello_world_shell.html",
        component_name="HelloWorld",
        props=_example_context()["app_props_server_render"],
        dom_id="HelloWorld-react-component-stream",
    )


def rsc_hello_world(request: HttpRequest) -> StreamingHttpResponse:
    return _streaming_shell_response(
        request,
        template_name="rsc_hello_world_shell.html",
        component_name="RscApp",
        props=_example_context()["rsc_props"],
        dom_id="RscApp-react-component-rsc",
        server_render_method="rsc",
    )


def client_side_hello_world_with_options(request: HttpRequest) -> HttpResponse:
    return render(request, "client_side_hello_world_with_options.html", _example_context())


def server_render_js_example(request: HttpRequest) -> HttpResponse:
    return render(request, "server_render_js_example.html", _example_context())


def metadata_example(request: HttpRequest) -> HttpResponse:
    context = _example_context()
    context["metadata_component"] = render_react_component_hash(
        "MetadataMessage",
        props=context["app_props_server_render"],
        request=request,
        prerender=True,
        trace=True,
        id="MetadataMessage-react-component-0",
    )
    return render(request, "metadata_example.html", context)
