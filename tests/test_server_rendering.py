from __future__ import annotations

import json

import httpcore
import pytest
from asgiref.sync import async_to_sync

from react_on_django.component import _resolve_render_options, render_react_component
from react_on_django.renderer.base import RegisteredStore
from react_on_django.renderer.rsc_renderer import RSCRenderer
from react_on_django.server_rendering import (
    RSC_PAYLOAD_CONTENT_TYPE,
    RendererBundle,
    RendererHTTPError,
    ServerRenderResult,
    build_js_evaluation_request,
    build_streaming_rendering_request,
    perform_server_render,
    resolve_renderer_bundle,
)
from react_on_django.views import rsc_payload_response, stream_react_component_response


class _BytesResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload.encode("utf-8")
        self.status = 200

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        return None


class _StreamResponse:
    def __init__(self, *lines: str) -> None:
        self._lines = [line.encode("utf-8") for line in lines]
        self.status = 200

    def iter_stream(self):
        return iter(self._lines)

    def close(self) -> None:
        return None


def _response_body(response) -> str:
    if response.is_async:
        async def collect() -> bytes:
            chunks: list[bytes] = []
            async for chunk in response.streaming_content:
                chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
            return b"".join(chunks)

        return async_to_sync(collect)().decode("utf-8")

    return b"".join(
        chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
        for chunk in response.streaming_content
    ).decode("utf-8")


def _write_renderer_manifest(tmp_project, sample_manifest_data):
    manifest_path = tmp_project / "public" / "packs" / "manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest_data))
    (tmp_project / "public" / "packs" / "server-bundle-xyz789.js").write_text("// server bundle")
    (tmp_project / "public" / "packs" / "rsc-bundle.js").write_text("// rsc bundle")


def test_prerendered_component_renders_server_html_and_merges_client_props(
    settings,
    tmp_project,
    sample_manifest_data,
    rf,
    monkeypatch,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    _write_renderer_manifest(tmp_project, sample_manifest_data)

    captured: dict[str, object] = {}

    def fake_open_request(url, fields, *, bundles=(), stream):
        captured["url"] = url
        captured["fields"] = fields
        captured["bundles"] = bundles
        captured["stream"] = stream
        return _BytesResponse(
            json.dumps(
                {
                    "html": "<h1>SSR Ada</h1>",
                    "clientProps": {"booted": True},
                    "consoleReplayScript": "console.log('server');",
                    "hasErrors": False,
                }
            )
        )

    monkeypatch.setattr("react_on_django.server_rendering._open_request", fake_open_request)

    markup = render_react_component(
        "HelloWorld",
        props={"name": "Ada"},
        request=rf.get("/ssr"),
        prerender=True,
    )

    assert "/bundles/server-bundle-xyz789.js/render/" in captured["url"]
    assert captured["bundles"] == ()
    assert captured["stream"] is False
    assert '<div id="HelloWorld-react-component"><h1>SSR Ada</h1></div>' in markup
    assert '"booted":true' in markup
    assert '"name":"Ada"' in markup
    assert 'id="consoleReplayLog"' in markup


def test_renderer_retries_with_uploaded_bundle_after_410(
    settings,
    tmp_project,
    sample_manifest_data,
    monkeypatch,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    _write_renderer_manifest(tmp_project, sample_manifest_data)

    bundle = resolve_renderer_bundle("server-bundle.js")
    attempts: list[tuple[tuple[RendererBundle, ...], bool]] = []

    def fake_open_request(url, fields, *, bundles=(), stream):
        attempts.append((tuple(bundles), stream))
        if len(attempts) == 1:
            raise RendererHTTPError(status=410, body=b"No bundle uploaded")
        return _BytesResponse(
            json.dumps({"html": "<div>ok</div>", "consoleReplayScript": "", "hasErrors": False})
        )

    monkeypatch.setattr("react_on_django.server_rendering._open_request", fake_open_request)

    result = perform_server_render(rendering_request="return 1", bundle=bundle)

    assert result.html == "<div>ok</div>"
    assert attempts[0] == ((), False)
    assert attempts[1][1] is False
    assert [uploaded.logical_name for uploaded in attempts[1][0]] == ["server-bundle.js"]


def test_ssr_connection_error_message_is_actionable(
    settings,
    tmp_project,
    sample_manifest_data,
    monkeypatch,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    _write_renderer_manifest(tmp_project, sample_manifest_data)

    bundle = resolve_renderer_bundle("server-bundle.js")

    def fake_open_request(url, fields, *, bundles=(), stream):
        raise httpcore.ConnectError("connection refused")

    monkeypatch.setattr("react_on_django.server_rendering._open_request", fake_open_request)

    with pytest.raises(Exception) as exc_info:
        perform_server_render(rendering_request="return 1", bundle=bundle)

    assert "could not connect to the rendering server" in str(exc_info.value)


def test_stream_react_component_response_streams_markup_and_scripts(
    settings,
    tmp_project,
    sample_manifest_data,
    rf,
    monkeypatch,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    _write_renderer_manifest(tmp_project, sample_manifest_data)

    def fake_stream_server_render(*, rendering_request, bundle, dependency_bundles=()):
        yield ServerRenderResult(
            html="<span>alpha</span>",
            client_props=None,
            console_replay_script="",
            has_errors=False,
            rendering_error=None,
        )
        yield ServerRenderResult(
            html="<span>beta</span>",
            client_props={"stage": "stream"},
            console_replay_script="console.log('stream');",
            has_errors=False,
            rendering_error=None,
        )

    monkeypatch.setattr(
        "react_on_django.renderer.streaming_renderer.stream_server_render",
        fake_stream_server_render,
    )

    response = stream_react_component_response(
        rf.get("/stream"),
        "HelloWorld",
        props={"name": "Ada"},
        id="hello-stream",
    )

    body = _response_body(response)

    assert 'id="js-react-on-rails-context"' in body
    assert '<div id="hello-stream">' in body
    assert "<span>alpha</span>" in body
    assert "<span>beta</span>" in body
    assert '"stage":"stream"' in body
    assert 'id="consoleReplayLog"' in body


def test_stream_react_component_response_accepts_rsc_render_mode_override(monkeypatch, rf):
    captured = {}

    def fake_stream(self, options, *, include_context_script):
        captured["server_render_method"] = options.server_render_method
        captured["include_context_script"] = include_context_script
        yield "<div>rsc stream</div>"

    monkeypatch.setattr(
        "react_on_django.renderer.streaming_renderer.StreamingRenderer.stream",
        fake_stream,
    )

    response = stream_react_component_response(
        rf.get("/rsc"),
        "HelloWorld",
        props={"name": "Ada"},
        server_render_method="rsc",
    )

    assert _response_body(response) == "<div>rsc stream</div>"
    assert captured == {
        "server_render_method": "rsc",
        "include_context_script": True,
    }


def test_build_streaming_rendering_request_initializes_registered_store_dependencies():
    request = build_streaming_rendering_request(
        component_name="HelloWorld",
        dom_id="hello-stream",
        props_json='{"name":"Ada"}',
        page_context={"serverSide": False},
        trace=True,
        registered_stores=(
            RegisteredStore(
                name="helloWorldStore",
                props_json='{"helloWorldData":{"name":"Ada"}}',
            ),
        ),
        store_dependencies=("helloWorldStore",),
    )

    assert 'ReactOnRails.clearHydratedStores();' in request
    assert 'ReactOnRails.getStoreGenerator("helloWorldStore")' in request
    assert 'ReactOnRails.setStore("helloWorldStore", store);' in request


def test_build_js_evaluation_request_marks_server_side_context():
    request = build_js_evaluation_request(
        js_expression="'<div>ok</div>'",
        page_context={"href": "http://example.test/"},
        throw_js_errors=False,
    )

    assert '"serverSide":true' in request
    assert "ReactOnRails.getConsoleReplayScript" in request


def test_rsc_payload_response_streams_payload(monkeypatch, rf):
    def fake_stream_payload(self, options):
        assert options.server_render_method == "rsc"
        yield "part-1"
        yield "part-2"

    monkeypatch.setattr(
        "react_on_django.renderer.rsc_renderer.RSCRenderer.stream_payload",
        fake_stream_payload,
    )

    response = rsc_payload_response(rf.get("/react_on_django/rsc/HelloWorld/"), "HelloWorld")

    assert response["Content-Type"] == RSC_PAYLOAD_CONTENT_TYPE
    assert _response_body(response) == "part-1part-2"


def test_rsc_renderer_stream_payload_serializes_renderer_results(monkeypatch, settings, rf):
    settings.REACT_ON_DJANGO = {
        "random_dom_id": False,
        "react_client_manifest_file": "react-client-manifest.json",
        "react_server_client_manifest_file": "react-server-client-manifest.json",
    }

    monkeypatch.setattr(
        "react_on_django.renderer.rsc_renderer.resolve_renderer_bundle",
        lambda logical_name: RendererBundle(
            logical_name=logical_name,
            bundle_id=f"{logical_name}-bundle",
            compiled_path=None,
            upload_filename=logical_name,
        ),
    )

    def fake_stream_server_render(*, rendering_request, bundle, dependency_bundles=()):
        yield ServerRenderResult(
            html='1:{"name":"RscHelloWorld"}',
            client_props=None,
            console_replay_script="console.log('payload');",
            has_errors=False,
            rendering_error=None,
            is_shell_ready=True,
        )

    monkeypatch.setattr(
        "react_on_django.renderer.rsc_renderer.stream_server_render",
        fake_stream_server_render,
    )

    options = _resolve_render_options(
        "RscHelloWorld",
        props={"name": "Ada"},
        request=rf.get("/react_on_django/rsc/RscHelloWorld/"),
        prerender=True,
        server_render_method="rsc",
    )

    payload = "".join(RSCRenderer().stream_payload(options)).strip()
    parsed = json.loads(payload)

    assert parsed == {
        "html": '1:{"name":"RscHelloWorld"}',
        "consoleReplayScript": "console.log('payload');",
        "hasErrors": False,
        "renderingError": None,
        "isShellReady": True,
    }


def test_streaming_renderer_uploads_rsc_bundle_as_dependency_when_manifests_are_configured(
    monkeypatch,
    settings,
    rf,
):
    settings.REACT_ON_DJANGO = {
        "random_dom_id": False,
        "react_client_manifest_file": "react-client-manifest.json",
        "react_server_client_manifest_file": "react-server-client-manifest.json",
        "server_bundle_js_file": "server-bundle.js",
        "rsc_bundle_js_file": "rsc-bundle.js",
    }

    bundles = {
        "server-bundle.js": RendererBundle(
            logical_name="server-bundle.js",
            bundle_id="server-bundle",
            compiled_path=None,
            upload_filename="server-bundle.js",
        ),
        "rsc-bundle.js": RendererBundle(
            logical_name="rsc-bundle.js",
            bundle_id="rsc-bundle",
            compiled_path=None,
            upload_filename="rsc-bundle.js",
        ),
    }

    monkeypatch.setattr(
        "react_on_django.renderer.streaming_renderer.resolve_renderer_bundle",
        lambda logical_name: bundles[logical_name],
    )

    captured: dict[str, object] = {}

    def fake_stream_server_render(*, rendering_request, bundle, dependency_bundles=()):
        captured["bundle"] = bundle
        captured["dependency_bundles"] = dependency_bundles
        yield ServerRenderResult(
            html="<span>alpha</span>",
            client_props=None,
            console_replay_script="",
            has_errors=False,
            rendering_error=None,
        )

    monkeypatch.setattr(
        "react_on_django.renderer.streaming_renderer.stream_server_render",
        fake_stream_server_render,
    )

    response = stream_react_component_response(
        rf.get("/stream"),
        "RscApp",
        props={"name": "Ada"},
        server_render_method="streaming",
    )

    assert "<span>alpha</span>" in _response_body(response)
    assert captured == {
        "bundle": bundles["server-bundle.js"],
        "dependency_bundles": (bundles["rsc-bundle.js"],),
    }


def test_streaming_request_injects_rsc_runtime_context_when_manifests_are_configured(
    settings,
    tmp_project,
    sample_manifest_data,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    settings.REACT_ON_DJANGO = {
        "ror_pro": True,
        "react_client_manifest_file": "packs/react-client-manifest.json",
        "react_server_client_manifest_file": "packs/react-server-client-manifest.json",
    }
    _write_renderer_manifest(tmp_project, sample_manifest_data)

    rendering_request = build_streaming_rendering_request(
        component_name="HelloWorld",
        dom_id="hello-stream",
        props_json='{"name":"Ada"}',
        page_context={"serverSide": False, "rorPro": True},
        trace=True,
        rsc_bundle=resolve_renderer_bundle("rsc-bundle.js"),
    )

    assert (
        'railsContext.reactClientManifestFileName = "packs/react-client-manifest.json";'
    ) in rendering_request
    assert (
        'railsContext.reactServerClientManifestFileName = '
        '"packs/react-server-client-manifest.json";'
    ) in rendering_request
    assert "serverSideRSCPayloadParameters" in rendering_request
    assert "globalThis.generateRSCPayload = async function generateRSCPayload" in rendering_request
    assert "typeof payload.exceptionMessage === 'string'" in rendering_request
    assert "typeof payload.getReader === 'function'" in rendering_request
    assert "new PassThrough()" in rendering_request
    assert "ReactOnRails.isRSCBundle ?" in rendering_request
