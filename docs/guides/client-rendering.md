# Client Rendering

Client rendering is the default mode. The server outputs:

- a shared page context script
- an empty DOM container
- a component spec script containing the serialized props

That means you can adopt the package without a running Node renderer.

Example:

```django
{% react_component "HelloWorld" props=hello_props prerender=False %}
```

The resulting markup preserves the shared runtime contract:

- `js-react-on-rails-context`
- `js-react-on-rails-component`
- `data-component-name`
- `data-dom-id`

This compatibility is intentional. It lets the existing ShakaCode browser
runtime continue to hydrate Django-rendered pages.

## HTML options

You can pass `html_options` and direct HTML attributes:

```django
{% react_component "HelloWorld"
    props=hello_props
    id="hello-root"
    html_options=hello_world_html_options
%}
```

Nested `data` and `aria` maps are flattened into HTML attributes.
