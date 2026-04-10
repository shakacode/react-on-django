from __future__ import annotations

from django.urls import path

from .views import rsc_payload_view

app_name = "react_on_django"

urlpatterns = [
    path("rsc/<str:component_name>", rsc_payload_view),
    path("rsc/<str:component_name>/", rsc_payload_view, name="rsc_payload"),
]
