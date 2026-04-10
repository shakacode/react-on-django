from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RegisteredStore:
    name: str
    props_json: str
    immediate_hydration: bool | None = None


@dataclass(frozen=True, slots=True)
class ResolvedRenderOptions:
    component_name: str
    dom_id: str
    html_options: Mapping[str, Any]
    page_context: Mapping[str, Any]
    prerender: bool
    props_json: str
    trace: bool
    replay_console: bool
    raise_on_prerender_error: bool
    server_render_method: str
    store_dependencies: tuple[str, ...] | None = None
    immediate_hydration: bool | None = None
    auto_load_bundle: bool = False
    registered_stores: tuple[RegisteredStore, ...] = ()


@dataclass(frozen=True, slots=True)
class ComponentMarkup:
    html: str
    script: str
    markup: str
    dom_id: str
    component_name: str
    props_json: str
    extra: Mapping[str, Any] | None = None

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            if self.extra and item in self.extra:
                return self.extra[item]
            raise KeyError(item) from None

    def __getattr__(self, item: str) -> Any:
        if self.extra and item in self.extra:
            return self.extra[item]
        raise AttributeError(item)


class BaseRenderer(ABC):
    @abstractmethod
    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        raise NotImplementedError
