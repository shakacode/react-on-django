from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("client_side_hello_world/", views.client_side_hello_world, name="client_side_hello_world"),
    path(
        "client_side_hello_world_shared_store/",
        views.client_side_hello_world_shared_store,
        name="client_side_hello_world_shared_store",
    ),
    path(
        "server_side_hello_world_shared_store/",
        views.server_side_hello_world_shared_store,
        name="server_side_hello_world_shared_store",
    ),
    path("server_side_hello_world/", views.server_side_hello_world, name="server_side_hello_world"),
    path("streaming_hello_world/", views.streaming_hello_world, name="streaming_hello_world"),
    path("rsc_hello_world/", views.rsc_hello_world, name="rsc_hello_world"),
    path(
        "client_side_hello_world_with_options/",
        views.client_side_hello_world_with_options,
        name="client_side_hello_world_with_options",
    ),
    path(
        "server_render_js_example/",
        views.server_render_js_example,
        name="server_render_js_example",
    ),
    path("metadata_example/", views.metadata_example, name="metadata_example"),
    path("react_on_django/", include("react_on_django.urls")),
    re_path(
        r"^packs/(?P<path>.*)$",
        serve,
        {"document_root": Path(settings.BASE_DIR) / "public" / "packs"},
    ),
    re_path(
        r"^packs-test/(?P<path>.*)$",
        serve,
        {"document_root": Path(settings.BASE_DIR) / "public" / "packs-test"},
    ),
]
