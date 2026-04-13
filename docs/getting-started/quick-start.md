# Quick Start

This is the shortest path from a Django template to a mounted React component.

## 1. Register a browser bundle

Build a client bundle that registers your components with the shared runtime:

```jsx
import RuntimeBridge from "react-on-rails/client";
import HelloWorld from "../components/HelloWorld";

RuntimeBridge.register({ HelloWorld });
```

## 2. Render assets in the layout

```django
{% load react %}
<!doctype html>
<html>
  <head>
    {% react_component_assets %}
  </head>
  <body>
    {% block content %}{% endblock %}
  </body>
</html>
```

`react_component_assets` resolves your browser entrypoints through
`django-rspack`, so the page expects a current manifest from your frontend
build.

## 3. Render a component from a template

```django
{% extends "base.html" %}
{% load react %}

{% block content %}
  {% react_component "HelloWorld" props=hello_props id="hello-world-root" %}
{% endblock %}
```

## 4. Pass props from the Django view

```python
def homepage(request):
    return render(
        request,
        "homepage.html",
        {"hello_props": {"helloWorldData": {"name": "Ada"}}},
    )
```

## 5. Enable SSR when ready

```django
{% react_component "HelloWorld" props=hello_props prerender=True %}
```

That only requires a renderer server once you actually enable prerendering.
