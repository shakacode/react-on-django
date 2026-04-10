from __future__ import annotations

import argparse
import html
import json
import re
import threading
from collections.abc import Mapping
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

COMPONENT_NAME_RE = re.compile(r'componentName\s*=\s*"(?P<name>[^"]+)"')
PROPS_RE = re.compile(
    r"usedProps\s*=\s*typeof props === 'undefined' \? (?P<props>.+?) : props;",
    re.DOTALL,
)


def _parse_request_payload(content_type: str, body: bytes) -> tuple[dict[str, str], set[str]]:
    if content_type.startswith("application/x-www-form-urlencoded"):
        data = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return {key: values[-1] for key, values in data.items()}, set()

    if not content_type.startswith("multipart/form-data"):
        return {}, set()

    parser = BytesParser(policy=default)
    message = parser.parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    fields: dict[str, str] = {}
    uploaded_bundle_fields: set[str] = set()

    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue

        payload = part.get_payload(decode=True) or b""
        if part.get_filename():
            uploaded_bundle_fields.add(name)
            continue

        fields[name] = payload.decode("utf-8")

    return fields, uploaded_bundle_fields


def _extract_component_name(rendering_request: str) -> str:
    match = COMPONENT_NAME_RE.search(rendering_request)
    if not match:
        return "UnknownComponent"
    return match.group("name")


def _extract_props(rendering_request: str) -> Mapping[str, object]:
    match = PROPS_RE.search(rendering_request)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group("props").strip())
    except json.JSONDecodeError:
        return {}

    if isinstance(parsed, dict):
        return parsed
    return {"value": parsed}


def _extract_name_from_props(props: Mapping[str, object]) -> str:
    hello_data = props.get("helloWorldData")
    if isinstance(hello_data, dict):
        name = hello_data.get("name")
        if isinstance(name, str) and name:
            return name
    name = props.get("name")
    if isinstance(name, str) and name:
        return name
    return "Renderer"


def _extract_note_from_props(props: Mapping[str, object]) -> str:
    hello_data = props.get("helloWorldData")
    if isinstance(hello_data, dict):
        note = hello_data.get("note")
        if isinstance(note, str):
            return note
    note = props.get("note")
    if isinstance(note, str):
        return note
    return ""


def _render_hello_world_markup(props: Mapping[str, object]) -> str:
    display_name = html.escape(_extract_name_from_props(props))
    note = html.escape(_extract_note_from_props(props))
    note_html = f'<p class="hello-world__note">{note}</p>' if note else ""
    return (
        '<div class="hello-world">'
        f'<h3 class="hello-world__title">Hello, {display_name}!</h3>'
        '<p class="hello-world__controls">Say hello to:'
        f'<input class="hello-world__input" type="text" value="{display_name}" />'
        "</p>"
        f"{note_html}"
        "</div>"
    )


class FakeRendererHandler(BaseHTTPRequestHandler):
    require_upload = False
    expected_password = ""
    first_miss_lock = threading.Lock()
    first_miss_paths: set[str] = set()

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        content_type = self.headers.get("Content-Type", "")
        raw_body = self.rfile.read(content_length)
        fields, uploaded_bundle_fields = _parse_request_payload(content_type, raw_body)

        password = fields.get("password", "")
        if self.expected_password and password != self.expected_password:
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.end_headers()
            self.wfile.write(b"Wrong password")
            return

        if self.require_upload and not uploaded_bundle_fields:
            with self.first_miss_lock:
                if self.path not in self.first_miss_paths:
                    self.first_miss_paths.add(self.path)
                    self.send_response(HTTPStatus.GONE)
                    self.end_headers()
                    self.wfile.write(b"Missing bundle upload")
                    return

        rendering_request = fields.get("renderingRequest", "")
        component_name = _extract_component_name(rendering_request)
        props = _extract_props(rendering_request)
        markup = _render_hello_world_markup(props)

        if "serverRenderReactComponent" in rendering_request:
            self._write_json_response(
                {
                    "html": markup,
                    "clientProps": {"rendererMode": "ssr"},
                    "consoleReplayScript": "console.log('fake renderer ssr');",
                    "hasErrors": False,
                }
            )
            return

        if "serverSideRSCPayloadParameters" in rendering_request:
            payload = json.dumps(props, separators=(",", ":"))
            lines = [
                {
                    "html": f"payload:{component_name}:{payload}\n",
                    "consoleReplayScript": "",
                    "hasErrors": False,
                }
            ]
            self._write_ndjson_response(lines)
            return

        if "streamServerRenderedReactComponent" in rendering_request:
            stream_mode = (
                "rsc" if "rscPayloadGenerationUrlPath" in rendering_request else "streaming"
            )
            split_point = markup.find("<p class=")
            if split_point == -1:
                split_point = len(markup) // 2
            lines = [
                {
                    "html": markup[:split_point],
                    "consoleReplayScript": "",
                    "hasErrors": False,
                },
                {
                    "html": markup[split_point:],
                    "clientProps": {"rendererMode": stream_mode},
                    "consoleReplayScript": f"console.log('fake renderer {stream_mode}');",
                    "hasErrors": False,
                },
            ]
            self._write_ndjson_response(lines)
            return

        self.send_response(HTTPStatus.BAD_REQUEST)
        self.end_headers()
        self.wfile.write(b"Unknown rendering request")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        _ = format, args

    def _write_json_response(self, payload: Mapping[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_ndjson_response(self, lines: list[Mapping[str, object]]) -> None:
        body = "".join(json.dumps(line) + "\n" for line in lines).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/x-component; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fake React on Django renderer server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3510)
    parser.add_argument("--password", default="")
    parser.add_argument("--require-upload", action="store_true")
    args = parser.parse_args()

    FakeRendererHandler.expected_password = args.password
    FakeRendererHandler.require_upload = args.require_upload

    server = ThreadingHTTPServer((args.host, args.port), FakeRendererHandler)
    print(f"fake renderer listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
