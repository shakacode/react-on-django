# Server Rendering

Server rendering uses the shared ShakaCode Node renderer over HTTP.

Enable it per render:

```django
{% react_component "HelloWorld" props=hello_props prerender=True %}
```

The Python transport handles:

- renderer URL configuration
- protocol version and password fields
- retry-on-`410` bundle upload
- `clientProps` merging
- console replay script passthrough

If the renderer is unavailable, the error message is designed to be actionable:

> SSR failed: could not connect to the rendering server at ...

## Required settings

```python
REACT_ON_DJANGO = {
    "server_bundle_js_file": "server-bundle.js",
    "rendering_server_url": "http://localhost:3500",
}
```

## Local smoke test

The example app includes a fake renderer that exercises the same HTTP contract:

```bash
cd example
./bin/dev --assets=build --renderer=fake
```
