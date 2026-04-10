from __future__ import annotations

from contextvars import ContextVar

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import HttpRequest

from .renderer.base import RegisteredStore

_current_request: ContextVar[HttpRequest | None] = ContextVar(
    "react_on_django_current_request",
    default=None,
)
_registered_stores: ContextVar[tuple[RegisteredStore, ...]] = ContextVar(
    "react_on_django_registered_stores",
    default=(),
)
_deferred_stores: ContextVar[tuple[RegisteredStore, ...]] = ContextVar(
    "react_on_django_deferred_stores",
    default=(),
)
_context_emitted: ContextVar[bool] = ContextVar(
    "react_on_django_context_emitted",
    default=False,
)


def get_current_request() -> HttpRequest | None:
    return _current_request.get()


def get_registered_stores() -> tuple[RegisteredStore, ...]:
    return _registered_stores.get()


def get_registered_store_names() -> tuple[str, ...]:
    names: list[str] = []
    for store in get_registered_stores():
        if store.name not in names:
            names.append(store.name)
    return tuple(names)


def register_store(store: RegisteredStore, *, defer: bool) -> None:
    registered = [*get_registered_stores(), store]
    _registered_stores.set(tuple(registered))
    if defer:
        deferred = [*_deferred_stores.get(), store]
        _deferred_stores.set(tuple(deferred))


def pop_deferred_stores() -> tuple[RegisteredStore, ...]:
    deferred = _deferred_stores.get()
    _deferred_stores.set(())
    return deferred


def should_emit_context_script() -> bool:
    if _context_emitted.get():
        return False
    _context_emitted.set(True)
    return True


def reset_helper_state() -> None:
    _registered_stores.set(())
    _deferred_stores.set(())
    _context_emitted.set(False)


class ReactOnDjangoRequestMiddleware:
    async_capable = True
    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self._is_async = iscoroutinefunction(get_response)
        if self._is_async:
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest):
        if self._is_async:
            return self.__acall__(request)

        request_token = _current_request.set(request)
        stores_token = _registered_stores.set(())
        deferred_token = _deferred_stores.set(())
        context_token = _context_emitted.set(False)
        try:
            return self.get_response(request)
        finally:
            _context_emitted.reset(context_token)
            _deferred_stores.reset(deferred_token)
            _registered_stores.reset(stores_token)
            _current_request.reset(request_token)

    async def __acall__(self, request: HttpRequest):
        request_token = _current_request.set(request)
        stores_token = _registered_stores.set(())
        deferred_token = _deferred_stores.set(())
        context_token = _context_emitted.set(False)
        try:
            return await self.get_response(request)
        finally:
            _context_emitted.reset(context_token)
            _deferred_stores.reset(deferred_token)
            _registered_stores.reset(stores_token)
            _current_request.reset(request_token)
