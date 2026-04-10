# Configuration

Package configuration lives under `REACT_ON_DJANGO` in Django settings.

Common keys:

```python
REACT_ON_DJANGO = {
    "bundle_name": "application",
    "server_bundle_js_file": "server-bundle.js",
    "rsc_bundle_js_file": "rsc-bundle.js",
    "prerender": False,
    "trace": False,
    "replay_console": True,
    "raise_on_prerender_error": True,
    "rendering_server_url": "http://localhost:3500",
    "rendering_server_password": "",
    "renderer_protocol_version": "2.0.0",
    "random_dom_id": False,
    "component_registry_timeout": 5000,
    "rsc_payload_generation_url_path": "/react_on_django/rsc/",
}
```

## Per-render overrides

Some options can be overridden when rendering:

- `prerender`
- `id`
- `trace`
- `replay_console`
- `raise_on_prerender_error`
- `random_dom_id`
- `server_render_method`

That lets one page stay client-rendered by default while another view opts into
streaming or RSC behavior explicitly.
