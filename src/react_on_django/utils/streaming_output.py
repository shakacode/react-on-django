from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Iterator
from typing import TypeVar

from asgiref.sync import sync_to_async
from django.http import HttpRequest

Chunk = TypeVar("Chunk")


def _next_chunk(iterator: Iterator[Chunk]) -> tuple[bool, Chunk | None]:
    try:
        return False, next(iterator)
    except StopIteration:
        return True, None


async def iter_as_async(stream: Iterable[Chunk]) -> AsyncIterator[Chunk]:
    iterator = iter(stream)
    try:
        while True:
            finished, chunk = await sync_to_async(_next_chunk, thread_sensitive=True)(iterator)
            if finished:
                break
            yield chunk
    finally:
        close = getattr(iterator, "close", None)
        if callable(close):
            await sync_to_async(close, thread_sensitive=True)()


def streaming_content_for_request(
    request: HttpRequest,
    stream: Iterable[Chunk],
) -> Iterable[Chunk] | AsyncIterator[Chunk]:
    meta = getattr(request, "META", {})
    if "wsgi.version" in meta:
        return stream
    if "asgi.version" in meta or hasattr(request, "scope"):
        return iter_as_async(stream)
    return stream
