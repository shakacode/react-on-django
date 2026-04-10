# Helper APIs

`react-on-django` exposes a few higher-level helpers beyond the basic
`react_component` tag.

## `react_component_hash`

Use `react_component_hash` when the server render function returns structured
markup, not just a single HTML string.

```django
{% react_component_hash "MetadataMessage" props=hello_props as component_data %}
{{ component_data.componentHtml|safe }}
```

This is the Django equivalent of the React on Rails render-hash pattern used
for metadata, head markup, and other multi-fragment render results.

## Shared stores

Use `react_redux_store` and `react_redux_store_hydration_data` when multiple
components should hydrate against the same registered store.

```django
{% react_redux_store "helloWorldStore" props=hello_props defer=True %}
{% react_component "HelloWorldFromStore" props=store_component_props %}
{% react_redux_store_hydration_data %}
```

The Python API is also available directly:

```python
from react_on_django import redux_store, redux_store_hydration_data
```

## `server_render_js`

Use `react_server_render_js` for direct node-side evaluation when you want
server output without a mounted React component.

```django
{% react_server_render_js "ReactOnRails.getComponent('HelloString').component.world()" %}
```

This keeps the shared renderer protocol but skips client hydration.

## Scaffolding commands

The package now includes basic starter commands:

```bash
python manage.py react_install
python manage.py react_generate dashboard-card
python manage.py react_generate posts-feed --rsc
```

`react_install` creates a starter `app/javascript/` layout with client, server,
and RSC bundle entrypoints. `react_generate` creates a component scaffold and,
unless you pass `--skip-register`, updates the relevant bundle registration
files.
