from __future__ import annotations

from .base import BaseRenderer, ComponentMarkup, ResolvedRenderOptions


class StreamingRenderer(BaseRenderer):
    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        raise NotImplementedError("Streaming SSR is not implemented yet.")
