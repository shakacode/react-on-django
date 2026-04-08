from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


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


@dataclass(frozen=True, slots=True)
class ComponentMarkup:
    html: str
    script: str
    markup: str
    dom_id: str
    component_name: str
    props_json: str

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class BaseRenderer(ABC):
    @abstractmethod
    def render(
        self,
        options: ResolvedRenderOptions,
        *,
        include_context_script: bool,
    ) -> ComponentMarkup:
        raise NotImplementedError
