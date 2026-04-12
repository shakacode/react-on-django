# React on Django

React on Django renders React components from Django templates with a Python
integration layer that stays compatible with the shared React on Rails
JavaScript runtime.

This initial scaffold covers:

- package metadata and tooling
- Django settings-backed configuration
- safe JSON and HTML output helpers
- `django-rspack` integration helpers for bundle tags and asset lookup
- client-only component rendering
- server-side rendering over the shared node renderer protocol
- streaming SSR and RSC response adapters
- Django template tags for `react_component` and `react_component_hash`
- store hydration helpers via `redux_store` and `redux_store_hydration_data`
- a `server_render_js` helper for raw node-side evaluation
- pytest coverage for the initial API surface

## Example app

The repository now includes a runnable Django example at `example/`. It ports
the supported integration scenarios from the upstream reference dummy app and
now also exercises the live SSR, streaming, and RSC adapters.

- the client-side HelloWorld page
- the `server_render_js` page for non-React server evaluation
- the `react_component_hash` metadata page
- a multi-component index page
- the shared-store pages for deferred and server-rendered hydration
- the HTML options example, including JSON-string props and nested `data-*` attributes

The example uses `django-rspack` for manifest-backed asset lookup and the shared
`react-on-rails` npm runtime for browser mounting and hydration.

Run the main validation paths with:

```bash
cd example && npm install
./bin/test-ci
./bin/dev dev
./bin/dev static
./bin/prod
```

Useful routes in the example app:

- `/`
- `/client_side_hello_world/`
- `/server_side_hello_world/`
- `/server_side_hello_world_shared_store/`
- `/server_render_js_example/`
- `/metadata_example/`
- `/streaming_hello_world/`
- `/rsc_hello_world/`
- `/client_side_hello_world_with_options/`

The Python package also exposes the helper APIs directly:

```python
from react_on_django import (
    redux_store,
    redux_store_hydration_data,
    render_react_component,
    render_react_component_hash,
    server_render_js,
)
```

The Django app now also ships management commands for starter scaffolding:

```bash
python manage.py react_install
python manage.py react_generate dashboard-card
python manage.py react_generate posts-feed --rsc
```

## Using with django-rspack

`react-on-django` uses `django-rspack` for compiled asset lookup. The component
renderer stays separate from the bundler, but React on Django exposes helpers so
the two packages fit together cleanly.

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "django_rspack",
    "react_on_django",
]

REACT_ON_DJANGO = {
    "bundle_name": "application",
}
```

```django
{% load react %}
<!DOCTYPE html>
<html>
<head>
  {% react_component_assets %}
</head>
<body>
  {% react_component "HelloWorld" props=hello_props %}
</body>
</html>
```

The integration helpers are also available from Python:

```python
from react_on_django.assets import (
    get_react_bundle_urls,
    get_server_bundle_path,
    render_react_component_assets,
)
```

## Licensing

React on Django is a single source-available product. The same package and docs
surface cover client rendering, SSR, streaming SSR, and React Server
Components.

- non-commercial and no-revenue use is free
- commercial production use requires a paid license from ShakaCode

See [LICENSE](/Users/justin/codex/react-on-django/LICENSE) for the repository
terms and [react-on-django.com/licensing](https://react-on-django.com/licensing)
for the public licensing page.
