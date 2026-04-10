from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpcore
from django.conf import settings

from .assets import resolve_bundle_file
from .conf import get_react_on_django_settings
from .errors import ReactOnDjangoError
from .renderer.base import RegisteredStore
from .utils.json_output import serialize_json

COMPONENT_HTML_KEY = "componentHtml"
RSC_PAYLOAD_CONTENT_TYPE = "application/x-ndjson; charset=utf-8"


@dataclass(frozen=True, slots=True)
class RendererBundle:
    logical_name: str
    bundle_id: str
    compiled_path: Path
    upload_filename: str


@dataclass(frozen=True, slots=True)
class ServerRenderResult:
    html: str | dict[str, Any] | None
    client_props: Any
    console_replay_script: str
    has_errors: bool
    rendering_error: Mapping[str, Any] | None
    is_shell_ready: bool | None = None


@dataclass(frozen=True, slots=True)
class RendererHTTPError(Exception):
    status: int
    body: bytes


class RendererResponse:
    def __init__(
        self,
        response: httpcore.Response,
        pool: httpcore.ConnectionPool,
        *,
        close_callback: Callable[[], None] | None = None,
    ) -> None:
        self.status = response.status
        self._response = response
        self._pool = pool
        self._close_callback = close_callback
        self._closed = False

    def read(self) -> bytes:
        return self._response.read()

    def iter_stream(self) -> Iterator[bytes]:
        return self._response.iter_stream()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._close_callback is not None:
                self._close_callback()
            else:
                self._response.close()
        finally:
            self._pool.close()


def resolve_renderer_bundle(bundle_name: str) -> RendererBundle:
    compiled_path = resolve_bundle_file(bundle_name)
    bundle_id = _build_bundle_identifier(bundle_name, compiled_path)
    return RendererBundle(
        logical_name=bundle_name,
        bundle_id=bundle_id,
        compiled_path=compiled_path,
        upload_filename=f"{bundle_id}.js",
    )


def build_ssr_rendering_request(
    *,
    component_name: str,
    dom_id: str,
    props_json: str,
    page_context: Mapping[str, Any],
    trace: bool,
    registered_stores: Sequence[RegisteredStore] = (),
    store_dependencies: Sequence[str] | None = None,
) -> str:
    return _build_rendering_request(
        component_name=component_name,
        dom_id=dom_id,
        props_json=props_json,
        page_context=page_context,
        trace=trace,
        render_function_name="serverRenderReactComponent",
        registered_stores=registered_stores,
        store_dependencies=store_dependencies,
    )


def build_streaming_rendering_request(
    *,
    component_name: str,
    dom_id: str,
    props_json: str,
    page_context: Mapping[str, Any],
    trace: bool,
    rsc_bundle: RendererBundle | None = None,
    registered_stores: Sequence[RegisteredStore] = (),
    store_dependencies: Sequence[str] | None = None,
) -> str:
    return _build_rendering_request(
        component_name=component_name,
        dom_id=dom_id,
        props_json=props_json,
        page_context=page_context,
        trace=trace,
        render_function_name="streamServerRenderedReactComponent",
        rsc_bundle=rsc_bundle,
        registered_stores=registered_stores,
        store_dependencies=store_dependencies,
    )


def build_rsc_rendering_request(
    *,
    component_name: str,
    dom_id: str,
    props_json: str,
    page_context: Mapping[str, Any],
    trace: bool,
    rsc_bundle: RendererBundle | None = None,
    registered_stores: Sequence[RegisteredStore] = (),
    store_dependencies: Sequence[str] | None = None,
) -> str:
    return _build_rendering_request(
        component_name=component_name,
        dom_id=dom_id,
        props_json=props_json,
        page_context=page_context,
        trace=trace,
        render_function_name="serverRenderRSCReactComponent",
        rsc_bundle=rsc_bundle,
        registered_stores=registered_stores,
        store_dependencies=store_dependencies,
    )


def build_js_evaluation_request(
    *,
    js_expression: str,
    page_context: Mapping[str, Any],
    throw_js_errors: bool,
) -> str:
    rails_context = dict(page_context)
    rails_context["serverSide"] = True
    return (
        "(function() {\n"
        f"  var railsContext = {serialize_json(rails_context)};\n"
        "  var htmlResult = '';\n"
        "  var consoleReplayScript = '';\n"
        "  var hasErrors = false;\n"
        "  var renderingErrorObject = null;\n"
        "  try {\n"
        "    htmlResult = (function() {\n"
        f"      return {js_expression};\n"
        "    })();\n"
        "  } catch (e) {\n"
        f"    if ({json.dumps(throw_js_errors)}) {{\n"
        "      throw e;\n"
        "    }\n"
        "    hasErrors = true;\n"
        "    renderingErrorObject = {\n"
        "      message: e && typeof e.message === 'string' ? e.message : String(e),\n"
        "      stack: e && e.stack ? String(e.stack) : null,\n"
        "    };\n"
        "    if (typeof ReactOnRails.handleError === 'function') {\n"
        "      htmlResult = ReactOnRails.handleError({\n"
        "        e: e,\n"
        "        name: null,\n"
        "        jsCode: null,\n"
        "        serverSide: true,\n"
        "      });\n"
        "    } else {\n"
        "      htmlResult = renderingErrorObject.message;\n"
        "    }\n"
        "  }\n"
        "  if (typeof ReactOnRails.getConsoleReplayScript === 'function') {\n"
        "    consoleReplayScript = ReactOnRails.getConsoleReplayScript();\n"
        "  }\n"
        "  return {\n"
        "    html: htmlResult,\n"
        "    consoleReplayScript: consoleReplayScript,\n"
        "    hasErrors: hasErrors,\n"
        "    renderingError: renderingErrorObject,\n"
        "  };\n"
        "})()"
    )


def perform_server_render(
    *,
    rendering_request: str,
    bundle: RendererBundle,
    dependency_bundles: Sequence[RendererBundle] = (),
) -> ServerRenderResult:
    response = _perform_renderer_request(
        rendering_request=rendering_request,
        bundle=bundle,
        dependency_bundles=dependency_bundles,
        stream=False,
    )
    try:
        return _parse_server_render_result(response.read())
    finally:
        response.close()


def stream_server_render(
    *,
    rendering_request: str,
    bundle: RendererBundle,
    dependency_bundles: Sequence[RendererBundle] = (),
) -> Iterator[ServerRenderResult]:
    response = _perform_renderer_request(
        rendering_request=rendering_request,
        bundle=bundle,
        dependency_bundles=dependency_bundles,
        stream=True,
    )
    return _iter_stream_results(response)


def merge_client_props(props_json: str, client_props: Any) -> str:
    if client_props is None:
        return props_json

    try:
        existing_props = json.loads(props_json)
    except json.JSONDecodeError as exc:
        raise ReactOnDjangoError(
            "Cannot merge renderer clientProps into props because "
            "the original props are not valid JSON."
        ) from exc

    if not isinstance(existing_props, dict):
        raise ReactOnDjangoError(
            "Cannot merge renderer clientProps into non-object props. "
            "Pass props as a dict or a JSON object string."
        )

    if not isinstance(client_props, dict):
        raise ReactOnDjangoError(
            "Expected renderer clientProps to be an object."
        )

    merged_props = dict(existing_props)
    merged_props.update(client_props)
    return serialize_json(merged_props)


def coerce_rendered_html(rendered_html: str | dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    if rendered_html is None:
        return "", {}

    if isinstance(rendered_html, str):
        return rendered_html, {}

    if not isinstance(rendered_html, dict):
        raise ReactOnDjangoError(
            f"Renderer returned unsupported html payload type: {type(rendered_html).__name__}."
        )

    component_html = rendered_html.get(COMPONENT_HTML_KEY)
    if component_html is None:
        raise ReactOnDjangoError(
            f"Renderer returned an object without the required '{COMPONENT_HTML_KEY}' key."
        )

    extra = dict(rendered_html)
    del extra[COMPONENT_HTML_KEY]
    return str(component_html), extra


def format_prerender_error(result: ServerRenderResult) -> str:
    detail = ""
    if result.rendering_error:
        message = result.rendering_error.get("message")
        stack = result.rendering_error.get("stack")
        detail_lines = [str(message)] if message else []
        if stack:
            detail_lines.append(str(stack))
        if detail_lines:
            detail = "\n\n" + "\n".join(detail_lines)
    return f"SSR failed while rendering the component.{detail}"


def _build_rendering_request(
    *,
    component_name: str,
    dom_id: str,
    props_json: str,
    page_context: Mapping[str, Any],
    trace: bool,
    render_function_name: str,
    rsc_bundle: RendererBundle | None = None,
    registered_stores: Sequence[RegisteredStore] = (),
    store_dependencies: Sequence[str] | None = None,
) -> str:
    rails_context = dict(page_context)
    rails_context["serverSide"] = True
    config = get_react_on_django_settings()
    if _rsc_support_enabled(config):
        rails_context["rscPayloadGenerationUrlPath"] = config.rsc_payload_generation_url_path

    render_function_expression = _render_function_expression(
        render_function_name,
        use_rsc_runtime=rsc_bundle is not None,
    )
    rsc_setup = _build_rsc_setup(config, rsc_bundle)
    store_setup = _build_store_setup(registered_stores, store_dependencies)

    return (
        "(function(componentName = "
        f"{json.dumps(component_name)}, props = undefined) {{\n"
        f"  var railsContext = {serialize_json(rails_context)};\n"
        f"{store_setup}"
        f"{rsc_setup}"
        "  var usedProps = typeof props === 'undefined' ? "
        f"{props_json} : props;\n"
        f"  return {render_function_expression}({{\n"
        "    name: componentName,\n"
        f"    domNodeId: {json.dumps(dom_id)},\n"
        "    props: usedProps,\n"
        f"    trace: {json.dumps(trace)},\n"
        "    railsContext: railsContext,\n"
        "    throwJsErrors: false,\n"
        "    renderingReturnsPromises: true,\n"
        "  });\n"
        "})()"
    )


def _build_store_setup(
    registered_stores: Sequence[RegisteredStore],
    store_dependencies: Sequence[str] | None,
) -> str:
    lines = ["  ReactOnRails.clearHydratedStores();\n"]
    if not registered_stores or not store_dependencies:
        return "".join(lines)

    dependency_names = list(dict.fromkeys(store_dependencies))
    selected_stores = [store for store in registered_stores if store.name in dependency_names]
    for store in selected_stores:
        lines.extend(
            [
                f"  var reduxProps = {store.props_json};\n",
                "  var storeGenerator = "
                f"ReactOnRails.getStoreGenerator({json.dumps(store.name)});\n",
                "  var store = storeGenerator(reduxProps, railsContext);\n",
                f"  ReactOnRails.setStore({json.dumps(store.name)}, store);\n",
            ]
        )
    return "".join(lines)


def _rsc_support_enabled(config: Any) -> bool:
    return bool(
        config.react_client_manifest_file and config.react_server_client_manifest_file
    )


def _render_function_expression(
    render_function_name: str,
    *,
    use_rsc_runtime: bool,
) -> str:
    if use_rsc_runtime:
        return (
            'ReactOnRails['
            'ReactOnRails.isRSCBundle ? '
            '"serverRenderRSCReactComponent" : '
            '"streamServerRenderedReactComponent"'
            "]"
        )
    return f"ReactOnRails[{json.dumps(render_function_name)}]"


def _build_rsc_setup(config: Any, rsc_bundle: RendererBundle | None) -> str:
    if not _rsc_support_enabled(config):
        return ""

    setup_lines = [
        (
            "  railsContext.reactClientManifestFileName = "
            f"{json.dumps(config.react_client_manifest_file)};\n"
        ),
        (
            "  railsContext.reactServerClientManifestFileName = "
            f"{json.dumps(config.react_server_client_manifest_file)};\n"
        ),
    ]
    if rsc_bundle is None:
        return "".join(setup_lines)

    setup_lines.extend(
        [
            "  railsContext.serverSideRSCPayloadParameters = {\n",
            "    renderingRequest: renderingRequest,\n",
            f"    rscBundleHash: {json.dumps(rsc_bundle.bundle_id)},\n",
            "  };\n",
            "  if (typeof generateRSCPayload !== 'function') {\n",
            (
                "    globalThis.generateRSCPayload = async function generateRSCPayload("
                "componentName, props, railsContext) {\n"
            ),
            (
                "      const { renderingRequest, rscBundleHash } = "
                "railsContext.serverSideRSCPayloadParameters;\n"
            ),
            "      const propsString = JSON.stringify(props);\n",
            (
                "      const newRenderingRequest = renderingRequest.replace("
                "/\\(\\s*\\)\\s*$/, "
                "`(${JSON.stringify(componentName)}, ${propsString})`);\n"
            ),
            "      const payload = await runOnOtherBundle(rscBundleHash, newRenderingRequest);\n",
            "      if (payload && typeof payload.exceptionMessage === 'string') {\n",
            "        throw new Error(payload.exceptionMessage);\n",
            "      }\n",
            "      if (payload && typeof payload.on === 'function') {\n",
            "        return payload;\n",
            "      }\n",
            "      if (payload && typeof payload.getReader === 'function') {\n",
            "        if (typeof PassThrough !== 'function') {\n",
            (
                "          throw new Error("
                "'PassThrough is required to bridge Web ReadableStream RSC payloads.'"
                ");\n"
            ),
            "        }\n",
            "        const bridgedStream = new PassThrough();\n",
            "        (async function bridgeReadableStream() {\n",
            "          const reader = payload.getReader();\n",
            "          try {\n",
            "            while (true) {\n",
            "              const { done, value } = await reader.read();\n",
            "              if (done) {\n",
            "                break;\n",
            "              }\n",
            "              if (typeof value === 'string') {\n",
            "                bridgedStream.write(value);\n",
            "              } else if (value) {\n",
            "                bridgedStream.write(Buffer.from(value));\n",
            "              }\n",
            "            }\n",
            "            bridgedStream.end();\n",
            "          } catch (error) {\n",
            "            bridgedStream.destroy(error);\n",
            "          }\n",
            "        })();\n",
            "        return bridgedStream;\n",
            "      }\n",
            "      if (typeof payload === 'string') {\n",
            "        if (typeof PassThrough !== 'function') {\n",
            (
                "          throw new Error("
                "'PassThrough is required to bridge string RSC payloads.'"
                ");\n"
            ),
            "        }\n",
            "        const bridgedStream = new PassThrough();\n",
            "        bridgedStream.end(payload);\n",
            "        return bridgedStream;\n",
            "      }\n",
            "      return payload;\n",
            "    };\n",
            "  }\n",
        ]
    )
    return "".join(setup_lines)


def _perform_renderer_request(
    *,
    rendering_request: str,
    bundle: RendererBundle,
    dependency_bundles: Sequence[RendererBundle],
    stream: bool,
):
    request_digest = hashlib.md5(rendering_request.encode("utf-8")).hexdigest()
    url = _render_url(bundle.bundle_id, request_digest)
    request_data = _build_form_fields(
        rendering_request=rendering_request,
        dependency_bundles=dependency_bundles,
    )

    try:
        return _open_request(url, request_data, stream=stream)
    except RendererHTTPError as error:
        if error.status == 410:
            uploaded_bundles = [bundle, *dependency_bundles]
            try:
                return _open_request(url, request_data, bundles=uploaded_bundles, stream=stream)
            except RendererHTTPError as retry_error:
                raise _translate_http_error(retry_error) from retry_error
        raise _translate_http_error(error) from error
    except (httpcore.NetworkError, httpcore.TimeoutException) as error:
        raise _connection_error(error) from error


def _render_url(bundle_id: str, request_digest: str) -> str:
    settings_obj = get_react_on_django_settings()
    base_url = settings_obj.rendering_server_url.rstrip("/") + "/"
    return urljoin(base_url, f"bundles/{bundle_id}/render/{request_digest}")


def _build_form_fields(
    *,
    rendering_request: str,
    dependency_bundles: Sequence[RendererBundle],
) -> list[tuple[str, str]]:
    config = get_react_on_django_settings()
    fields: list[tuple[str, str]] = [
        ("renderingRequest", rendering_request),
        ("protocolVersion", config.renderer_protocol_version),
        ("password", config.rendering_server_password),
        ("railsEnv", "development" if getattr(settings, "DEBUG", False) else "production"),
    ]
    if dependency_bundles:
        for dependency_bundle in dependency_bundles:
            fields.append(("dependencyBundleTimestamps[]", dependency_bundle.bundle_id))
    return fields


def _open_request(
    url: str,
    fields: Sequence[tuple[str, str]],
    *,
    bundles: Sequence[RendererBundle] = (),
    stream: bool,
):
    if bundles:
        files = [
            (
                f"bundle_{bundle.bundle_id}",
                bundle.upload_filename,
                "text/javascript",
                bundle.compiled_path.read_bytes(),
            )
            for bundle in bundles
        ]
        files.extend(_renderer_asset_uploads())
        body, content_type = _encode_multipart(
            fields,
            files=files,
        )
    else:
        body = "&".join(
            f"{_urlencode_key(key)}={_urlencode_value(value)}" for key, value in fields
        ).encode("utf-8")
        content_type = "application/x-www-form-urlencoded"

    try:
        return _send_renderer_request(
            url,
            body=body,
            content_type=content_type,
            force_http2_prior_knowledge=_should_force_http2_prior_knowledge(url),
            stream=stream,
        )
    except httpcore.ProtocolError:
        if _should_force_http2_prior_knowledge(url):
            return _send_renderer_request(
                url,
                body=body,
                content_type=content_type,
                force_http2_prior_knowledge=False,
                stream=stream,
            )
        raise


def _encode_multipart(
    fields: Sequence[tuple[str, str]],
    *,
    files: Sequence[tuple[str, str, str, bytes]],
) -> tuple[bytes, str]:
    boundary = f"react-on-django-{secrets.token_hex(12)}"
    lines: list[bytes] = []

    for key, value in fields:
        lines.extend(
            [
                f"--{boundary}".encode(),
                f'Content-Disposition: form-data; name="{key}"'.encode(),
                b"",
                value.encode("utf-8"),
            ]
        )

    for field_name, filename, content_type, payload in files:
        lines.extend(
            [
                f"--{boundary}".encode(),
                (
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{filename}"'
                ).encode(),
                f"Content-Type: {content_type}".encode(),
                b"",
                payload,
            ]
        )

    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    body = b"\r\n".join(lines)
    return body, f"multipart/form-data; boundary={boundary}"


def _renderer_asset_uploads() -> list[tuple[str, str, str, bytes]]:
    config = get_react_on_django_settings()
    if not _rsc_support_enabled(config):
        return []

    try:
        from django_rspack.conf import get_config
    except ImportError as exc:
        raise ReactOnDjangoError(
            "django-rspack is required for asset integration. "
            "Install django-rspack and add 'django_rspack' to INSTALLED_APPS."
        ) from exc

    public_output_path = get_config().public_output_path
    uploads: list[tuple[str, str, str, bytes]] = []
    for filename in (
        config.react_client_manifest_file,
        config.react_server_client_manifest_file,
    ):
        if filename is None:
            continue
        asset_path = public_output_path / filename
        if not asset_path.exists():
            raise ReactOnDjangoError(
                f"Required RSC manifest asset '{filename}' does not exist at {asset_path}. "
                "Build the RSC manifests before enabling React Server Components."
            )
        uploads.append(
            (
                f"asset_{asset_path.stem}",
                asset_path.name,
                "application/json",
                asset_path.read_bytes(),
            )
        )
    return uploads


def _urlencode_key(value: str) -> str:
    from urllib.parse import quote_plus

    return quote_plus(value)


def _urlencode_value(value: str) -> str:
    from urllib.parse import quote_plus

    return quote_plus(value)


def _parse_server_render_result(raw_body: bytes) -> ServerRenderResult:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ReactOnDjangoError(
            "Renderer returned invalid JSON for an SSR response."
        ) from exc
    return _deserialize_server_result(payload)


def _iter_stream_results(response) -> Iterator[ServerRenderResult]:
    pending = b""
    try:
        for raw_chunk in response.iter_stream():
            pending += raw_chunk
            while b"\n" in pending:
                raw_line, pending = pending.split(b"\n", 1)
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ReactOnDjangoError(
                        "Renderer returned an invalid JSON line while streaming."
                    ) from exc
                yield _deserialize_server_result(payload)
        if pending.strip():
            try:
                payload = json.loads(pending.decode("utf-8").strip())
            except json.JSONDecodeError as exc:
                raise ReactOnDjangoError(
                    "Renderer returned an invalid JSON line while streaming."
                ) from exc
            yield _deserialize_server_result(payload)
    finally:
        response.close()


def _deserialize_server_result(payload: Mapping[str, Any]) -> ServerRenderResult:
    return ServerRenderResult(
        html=payload.get("html"),
        client_props=payload.get("clientProps"),
        console_replay_script=str(payload.get("consoleReplayScript", "")),
        has_errors=bool(payload.get("hasErrors", False)),
        rendering_error=payload.get("renderingError"),
        is_shell_ready=payload.get("isShellReady"),
    )


def _translate_http_error(error: RendererHTTPError) -> ReactOnDjangoError:
    body = error.body.decode("utf-8", errors="replace")
    if error.status == 400:
        return ReactOnDjangoError(
            "SSR failed because the rendering server rejected the request "
            "or hit an unhandled VM error.\n\n"
            f"{body}"
        )
    if error.status == 401:
        return ReactOnDjangoError(
            "SSR failed because the rendering server rejected the password. "
            "Check REACT_ON_DJANGO['rendering_server_password']."
        )
    if error.status == 412:
        return ReactOnDjangoError(
            "SSR failed because the rendering server protocol is incompatible.\n\n"
            f"{body}"
        )
    return ReactOnDjangoError(
        f"SSR failed because the rendering server returned HTTP {error.status}.\n\n{body}"
    )


def _connection_error(error: BaseException) -> ReactOnDjangoError:
    url = get_react_on_django_settings().rendering_server_url
    return ReactOnDjangoError(
        "SSR failed: could not connect to the rendering server at "
        f"{url}. Start it with `npm run serve` or set prerender=False for client-only rendering."
    )


def _should_force_http2_prior_knowledge(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "http"


def _send_renderer_request(
    url: str,
    *,
    body: bytes,
    content_type: str,
    force_http2_prior_knowledge: bool,
    stream: bool,
) -> RendererResponse:
    timeout = get_react_on_django_settings().rendering_server_timeout
    pool = httpcore.ConnectionPool(
        http1=not force_http2_prior_knowledge,
        http2=True,
    )
    request_kwargs = {
        "headers": {"Content-Type": content_type},
        "content": body,
        "extensions": {
            "timeout": {
                "connect": timeout,
                "read": timeout,
                "write": timeout,
                "pool": timeout,
            }
        },
    }

    if stream:
        stream_context = pool.stream("POST", url, **request_kwargs)
        try:
            response = stream_context.__enter__()
        except BaseException:
            pool.close()
            raise

        if response.status >= 400:
            try:
                error_body = response.read()
            finally:
                stream_context.__exit__(None, None, None)
                pool.close()
            raise RendererHTTPError(status=response.status, body=error_body)

        return RendererResponse(
            response,
            pool,
            close_callback=lambda: stream_context.__exit__(None, None, None),
        )

    try:
        response = pool.request("POST", url, **request_kwargs)
    except BaseException:
        pool.close()
        raise

    if response.status >= 400:
        try:
            error_body = response.read()
        finally:
            response.close()
            pool.close()
        raise RendererHTTPError(status=response.status, body=error_body)
    return RendererResponse(response, pool)


def _build_bundle_identifier(bundle_name: str, compiled_path: Path) -> str:
    compiled_basename = compiled_path.name
    configured_basename = Path(bundle_name).name
    if compiled_basename != configured_basename:
        return compiled_basename
    digest = hashlib.md5(compiled_path.read_bytes()).hexdigest()
    env = "development" if getattr(settings, "DEBUG", False) else "production"
    return f"{digest}-{env}"
