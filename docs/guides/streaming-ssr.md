# Streaming SSR

Streaming SSR is exposed through `stream_react_component_response`, which
returns a `StreamingHttpResponse`.

This is the recommended entrypoint for Django views that need:

- a shell that flushes immediately
- progressive component HTML delivery
- ASGI-friendly streaming behavior

Example view pattern:

```python
from django.template.loader import render_to_string
from react_on_django.views import stream_react_component_response

def streaming_page(request):
    shell = render_to_string("streaming_shell.html", request=request)
    prefix, suffix = shell.split("<!--STREAM_COMPONENT-->", maxsplit=1)
    component_response = stream_react_component_response(
        request,
        "HelloWorld",
        props={"helloWorldData": {"name": "Ada"}},
        id="hello-stream",
        trace=True,
    )
```

The sample app has a full working implementation in
`example/react_on_django_example/views.py`.

## Current scope

The package already supports:

- streamed HTML shells through Django ASGI responses
- shared renderer console replay
- streamed RSC payload endpoints under `react_on_django.urls`

Broader controller-level template streaming and more of the upstream helper
surface are still being expanded.
