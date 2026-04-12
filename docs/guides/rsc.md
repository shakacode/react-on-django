# React Server Components

React Server Components support in `react-on-django` has two surfaces:

1. streamed HTML responses in RSC mode
2. a dedicated payload endpoint for nested server component payload generation

## Streamed HTML in RSC mode

For streamed HTML pages, use the streaming response helper with
`server_render_method="rsc"`:

```python
response = stream_react_component_response(
    request,
    "HelloWorld",
    props=hello_props,
    id="hello-rsc",
    server_render_method="rsc",
)
```

This preserves the HTML-streaming entrypoint while adding the RSC payload
generation URL to the shared runtime context.

## RSC payload endpoint

The built-in route lives at:

```text
/react_on_django/rsc/<component_name>/
```

It streams `application/x-ndjson` and accepts props through:

- `GET ?props=<json>`
- `POST` with a JSON request body

## Example routes

The sample app includes:

- `/rsc_hello_world/`
- `/react_on_django/rsc/HelloWorld/`

## Current scope

The payload endpoint and RSC-mode streaming shell are implemented. Additional
upstream helper APIs such as `rsc_payload_react_component`, cached helpers, and
broader RSC example coverage are still being ported.
