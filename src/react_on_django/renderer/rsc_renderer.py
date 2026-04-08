from __future__ import annotations

from .base import BaseRenderer, ComponentMarkup, ResolvedRenderOptions


class RSCRenderer(BaseRenderer):
    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        raise NotImplementedError("React Server Components are not implemented yet.")
