"""Public package exports for React on Django."""

__version__ = "0.1.0"

from .assets import (  # noqa: E402
    get_react_bundle_urls,
    get_server_bundle_path,
    get_server_bundle_url,
    render_generated_component_assets,
    render_generated_store_assets,
    render_react_component_assets,
)
from .component import (  # noqa: E402
    rails_context,
    redux_store,
    redux_store_hydration_data,
    render_rails_context,
    render_react_component,
    render_react_component_hash,
    server_render_js,
)
from .errors import ReactOnDjangoError  # noqa: E402
from .renderer.base import ComponentMarkup  # noqa: E402
from .utils.json_output import json_safe_and_pretty, sanitized_props_string  # noqa: E402
from .views import rsc_payload_response, stream_react_component_response  # noqa: E402

__all__ = [
    "ComponentMarkup",
    "ReactOnDjangoError",
    "get_react_bundle_urls",
    "get_server_bundle_path",
    "get_server_bundle_url",
    "json_safe_and_pretty",
    "rails_context",
    "redux_store",
    "redux_store_hydration_data",
    "render_generated_component_assets",
    "render_generated_store_assets",
    "render_react_component_assets",
    "render_rails_context",
    "render_react_component",
    "render_react_component_hash",
    "rsc_payload_response",
    "sanitized_props_string",
    "server_render_js",
    "stream_react_component_response",
]
