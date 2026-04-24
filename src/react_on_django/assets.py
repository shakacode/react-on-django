from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.utils.safestring import mark_safe

from .conf import get_react_on_django_settings
from .errors import ReactOnDjangoError
from .utils.html_output import (
    join_html_fragments,
    render_external_script_tag,
    render_stylesheet_tag,
)


def _django_rspack_asset_helpers():
    try:
        from django_rspack import get_asset_path, get_asset_url, get_bundle_urls
    except ImportError:
        try:
            from django_rspack.conf import get_config
            from django_rspack.manifest import get_manifest
        except ImportError as exc:
            raise ReactOnDjangoError(
                "django-rspack is required for asset integration. "
                "Install django-rspack and add 'django_rspack' to INSTALLED_APPS."
            ) from exc

        def _build_asset_url(path: str) -> str:
            asset_host = get_config().asset_host
            if asset_host:
                return f"{asset_host.rstrip('/')}{path}"
            return path

        def get_asset_path(name: str) -> str:
            return get_manifest().lookup_strict(name)

        def get_asset_url(name: str) -> str:
            return _build_asset_url(get_asset_path(name))

        def get_bundle_urls(name: str, *, pack_type: str = "js") -> tuple[str, ...]:
            manifest = get_manifest()
            chunks = manifest.lookup_pack_with_chunks(name, pack_type=pack_type)
            if chunks:
                paths = chunks
            else:
                paths = [manifest.lookup_strict(name, pack_type=pack_type)]

            seen: set[str] = set()
            urls: list[str] = []
            for path in paths:
                if path in seen:
                    continue
                seen.add(path)
                urls.append(_build_asset_url(path))
            return tuple(urls)

        return get_asset_path, get_asset_url, get_bundle_urls

    return get_asset_path, get_asset_url, get_bundle_urls


def _use_inline_dev_server_css() -> bool:
    try:
        from django_rspack.conf import get_config
    except ImportError:
        return False

    config = get_config()
    return bool(config.dev_server_hmr and config.dev_server_inline_css)


def _resolve_bundle_name(bundle_name: str | None) -> str:
    active_bundle_name = bundle_name or get_react_on_django_settings().bundle_name
    if not active_bundle_name:
        raise ReactOnDjangoError(
            "No React bundle name is configured. Pass bundle_name=... or set "
            "REACT_ON_DJANGO['bundle_name']."
        )
    return active_bundle_name


def get_react_bundle_urls(
    bundle_name: str | None = None,
    *,
    pack_type: str = "js",
) -> tuple[str, ...]:
    _, _, get_bundle_urls = _django_rspack_asset_helpers()
    try:
        return get_bundle_urls(_resolve_bundle_name(bundle_name), pack_type=pack_type)
    except Exception as exc:
        if pack_type == "css" and _use_inline_dev_server_css():
            try:
                from django_rspack.manifest import MissingEntryError
            except ImportError:
                MissingEntryError = ()
            if MissingEntryError and isinstance(exc, MissingEntryError):
                return ()
        raise


def get_server_bundle_path() -> str:
    get_asset_path, _, _ = _django_rspack_asset_helpers()
    return get_asset_path(get_react_on_django_settings().server_bundle_js_file)


def resolve_bundle_file(bundle_name: str) -> Path:
    get_asset_path, _, _ = _django_rspack_asset_helpers()

    try:
        from django_rspack.conf import get_config
    except ImportError as exc:
        raise ReactOnDjangoError(
            "django-rspack is required for asset integration. "
            "Install django-rspack and add 'django_rspack' to INSTALLED_APPS."
        ) from exc

    compiled_path = get_asset_path(bundle_name)
    parsed = urlsplit(compiled_path)
    if parsed.scheme or parsed.netloc:
        raise ReactOnDjangoError(
            f"Bundle '{bundle_name}' resolved to a remote URL ({compiled_path}). "
            "Server rendering requires a local compiled file. Run a local build and ensure "
            "the manifest points to a filesystem-backed asset."
        )

    resolved_path = get_config().public_root_path / parsed.path.lstrip("/")
    if not resolved_path.exists():
        raise ReactOnDjangoError(
            f"Bundle '{bundle_name}' was resolved to {resolved_path}, "
            "but that file does not exist. "
            "Build the server bundle before enabling prerendering."
        )

    return resolved_path


def get_server_bundle_url() -> str:
    _, get_asset_url, _ = _django_rspack_asset_helpers()
    return get_asset_url(get_react_on_django_settings().server_bundle_js_file)


def render_react_component_assets(
    bundle_name: str | None = None,
    *,
    include_css: bool = True,
    include_js: bool = True,
    defer: bool = True,
    async_attr: bool = False,
    script_attributes: dict[str, Any] | None = None,
    link_attributes: dict[str, Any] | None = None,
) -> str:
    active_bundle_name = _resolve_bundle_name(bundle_name)
    fragments: list[str] = []

    if include_css and not _use_inline_dev_server_css():
        for href in get_react_bundle_urls(active_bundle_name, pack_type="css"):
            fragments.append(render_stylesheet_tag(href, attributes=link_attributes))

    if include_js:
        for src in get_react_bundle_urls(active_bundle_name, pack_type="js"):
            fragments.append(
                render_external_script_tag(
                    src,
                    defer=defer,
                    async_attr=async_attr,
                    attributes=script_attributes,
                )
            )

    return mark_safe(join_html_fragments(*fragments))


def render_generated_component_assets(
    component_name: str,
    *,
    defer: bool = True,
    async_attr: bool = False,
    script_attributes: dict[str, Any] | None = None,
    link_attributes: dict[str, Any] | None = None,
) -> str:
    return _render_generated_bundle_assets(
        component_name,
        bundle_kind="component",
        include_css=True,
        defer=defer,
        async_attr=async_attr,
        script_attributes=script_attributes,
        link_attributes=link_attributes,
    )


def render_generated_store_assets(
    store_name: str,
    *,
    defer: bool = True,
    async_attr: bool = False,
    script_attributes: dict[str, Any] | None = None,
) -> str:
    return _render_generated_bundle_assets(
        store_name,
        bundle_kind="store",
        include_css=False,
        defer=defer,
        async_attr=async_attr,
        script_attributes=script_attributes,
        link_attributes=None,
    )


def _render_generated_bundle_assets(
    logical_name: str,
    *,
    bundle_kind: str,
    include_css: bool,
    defer: bool,
    async_attr: bool,
    script_attributes: dict[str, Any] | None,
    link_attributes: dict[str, Any] | None,
) -> str:
    generated_bundle_name = f"generated/{logical_name}"
    try:
        return render_react_component_assets(
            bundle_name=generated_bundle_name,
            include_css=include_css,
            include_js=True,
            defer=defer,
            async_attr=async_attr,
            script_attributes=script_attributes,
            link_attributes=link_attributes,
        )
    except Exception as exc:
        try:
            from django_rspack.manifest import MissingEntryError
        except ImportError:
            MissingEntryError = ()

        if MissingEntryError and isinstance(exc, MissingEntryError) and settings.DEBUG:
            raise ReactOnDjangoError(
                f"Auto-loaded {bundle_kind} bundle missing for '{logical_name}'. "
                "Expected the django-rspack manifest to contain the "
                f"'{generated_bundle_name}' entrypoint. "
                "Build the generated bundle or disable auto_load_bundle."
            ) from exc
        raise
