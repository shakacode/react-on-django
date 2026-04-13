# Introduction

`react-on-django` lets Django applications render React components from Django
templates while preserving the shared runtime contract used by the
ShakaCode React on Rails ecosystem.

The package is built around a few principles:

- Django developers should be able to render React from familiar template tags.
- Client rendering should work without a running Node renderer.
- SSR, streaming SSR, and React Server Components should reuse the shared
  JavaScript and Node renderer rather than reimplementing them in Python.
- Bundler integration should stay behind a seam, which is why asset lookup
  flows through `django-rspack`.

The primary template API is:

```django
{% load react %}
{% react_component "HelloWorld" props=hello_props %}
```

Most applications can start with client rendering and enable SSR, streaming
SSR, or RSC incrementally once the renderer-backed pieces are in place.

When you need prerendering:

```django
{% react_component "HelloWorld" props=hello_props prerender=True %}
```

When you need structured HTML and script fragments:

```django
{% react_component_hash "HelloWorld" props=hello_props as component_data %}
{{ component_data.html|safe }}
{{ component_data.script|safe }}
```

For live examples, see the sample app in `example/`.

The package also ships starter commands:

```bash
python manage.py react_install
python manage.py react_generate dashboard-card
python manage.py react_generate posts-feed --rsc
```
