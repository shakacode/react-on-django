from __future__ import annotations

from .base import BaseRenderer, ComponentMarkup, ResolvedRenderOptions


class ServerRenderer(BaseRenderer):
    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        raise NotImplementedError("Server-side rendering is not implemented yet.")
