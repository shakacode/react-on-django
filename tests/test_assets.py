from __future__ import annotations

import json
import sys
import types

from django.template import Context, Template
from django_rspack.manifest import MissingEntryError

import react_on_django.assets as assets
from react_on_django.assets import (
    get_react_bundle_urls,
    get_server_bundle_path,
    get_server_bundle_url,
    render_generated_component_assets,
    render_generated_store_assets,
    render_react_component_assets,
)


def _write_manifest(tmp_project, sample_manifest_data):
    manifest_path = tmp_project / "public" / "packs" / "manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest_data))


def test_get_react_bundle_urls_returns_chunk_order(settings, tmp_project, sample_manifest_data):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    _write_manifest(tmp_project, sample_manifest_data)

    assert get_react_bundle_urls("application", pack_type="js") == (
        "/packs/runtime-abc123.js",
        "/packs/vendor-789xyz.js",
        "/packs/application-abc123.js",
    )


def test_asset_helpers_fall_back_to_django_rspack_manifest_api(monkeypatch):
    fake_package = types.ModuleType("django_rspack")
    fake_package.__path__ = []

    fake_conf = types.ModuleType("django_rspack.conf")
    fake_manifest_module = types.ModuleType("django_rspack.manifest")

    class FakeConfig:
        asset_host = "https://cdn.example.com"

    class FakeManifest:
        def lookup_strict(self, name, pack_type=None):
            if pack_type:
                return f"/packs/{name}.{pack_type}"
            return f"/packs/{name}"

        def lookup_pack_with_chunks(self, name, pack_type=None):
            if name == "application" and pack_type == "js":
                return [
                    "/packs/runtime.js",
                    "/packs/vendor.js",
                    "/packs/vendor.js",
                    "/packs/application.js",
                ]
            return None

    fake_conf.get_config = FakeConfig
    fake_manifest_module.get_manifest = FakeManifest

    monkeypatch.setitem(sys.modules, "django_rspack", fake_package)
    monkeypatch.setitem(sys.modules, "django_rspack.conf", fake_conf)
    monkeypatch.setitem(sys.modules, "django_rspack.manifest", fake_manifest_module)

    get_asset_path, get_asset_url, get_bundle_urls = assets._django_rspack_asset_helpers()

    assert get_asset_path("server-bundle.js") == "/packs/server-bundle.js"
    assert get_asset_url("server-bundle.js") == "https://cdn.example.com/packs/server-bundle.js"
    assert get_bundle_urls("application", pack_type="js") == (
        "https://cdn.example.com/packs/runtime.js",
        "https://cdn.example.com/packs/vendor.js",
        "https://cdn.example.com/packs/application.js",
    )
    assert get_bundle_urls("admin", pack_type="css") == (
        "https://cdn.example.com/packs/admin.css",
    )


def test_render_react_component_assets_uses_configured_bundle(
    settings,
    tmp_project,
    sample_manifest_data,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    settings.REACT_ON_DJANGO = {"bundle_name": "application"}
    _write_manifest(tmp_project, sample_manifest_data)

    html = render_react_component_assets()

    assert '<link ' in html
    assert 'href="/packs/application-def456.css"' in html
    assert 'rel="stylesheet"' in html
    assert '<script src="/packs/runtime-abc123.js" defer></script>' in html
    assert '<script src="/packs/vendor-789xyz.js" defer></script>' in html
    assert '<script src="/packs/application-abc123.js" defer></script>' in html


def test_server_bundle_helpers_resolve_through_django_rspack(
    settings,
    tmp_project,
    sample_manifest_data,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {"asset_host": "https://cdn.example.com"}
    settings.REACT_ON_DJANGO = {"server_bundle_js_file": "server-bundle.js"}
    _write_manifest(tmp_project, sample_manifest_data)

    assert get_server_bundle_path() == "/packs/server-bundle-xyz789.js"
    assert get_server_bundle_url() == "https://cdn.example.com/packs/server-bundle-xyz789.js"


def test_react_component_assets_template_tag_renders_bundle(
    settings,
    tmp_project,
    sample_manifest_data,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    settings.REACT_ON_DJANGO = {"bundle_name": "application"}
    _write_manifest(tmp_project, sample_manifest_data)

    template = Template("{% load react %}{% react_component_assets %}")
    rendered = template.render(Context({}))

    assert '<link ' in rendered
    assert 'href="/packs/application-def456.css"' in rendered
    assert 'rel="stylesheet"' in rendered
    assert rendered.count("<script") == 3


def test_render_react_component_assets_skips_missing_css_in_hmr_mode(
    settings,
    tmp_project,
    sample_manifest_data,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {"dev_server": {"hmr": True}}
    settings.REACT_ON_DJANGO = {"bundle_name": "application"}
    manifest_without_css = dict(sample_manifest_data)
    manifest_without_css.pop("application.css", None)
    manifest_without_css["entrypoints"] = {
        "application": {
            "assets": {
                "js": list(sample_manifest_data["entrypoints"]["application"]["assets"]["js"]),
                "css": [],
            }
        }
    }
    _write_manifest(tmp_project, manifest_without_css)

    html = render_react_component_assets()

    assert "<link " not in html
    assert '<script src="/packs/runtime-abc123.js" defer></script>' in html


def test_missing_css_bundle_still_raises_when_hmr_is_disabled(
    settings,
    tmp_project,
    sample_manifest_data,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {"dev_server": {"hmr": False}}
    settings.REACT_ON_DJANGO = {"bundle_name": "application"}
    manifest_without_css = dict(sample_manifest_data)
    manifest_without_css.pop("application.css", None)
    manifest_without_css["entrypoints"] = {
        "application": {
            "assets": {
                "js": list(sample_manifest_data["entrypoints"]["application"]["assets"]["js"]),
                "css": [],
            }
        }
    }
    _write_manifest(tmp_project, manifest_without_css)

    try:
        render_react_component_assets()
    except MissingEntryError:
        pass
    else:
        raise AssertionError("Expected MissingEntryError when CSS is missing without HMR.")


def test_render_generated_component_assets_uses_generated_entrypoint(
    settings,
    tmp_project,
    sample_manifest_data,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    _write_manifest(tmp_project, sample_manifest_data)

    html = render_generated_component_assets("HelloWorld")

    assert 'href="/packs/generated-HelloWorld-aaa111.css"' in html
    assert '<script src="/packs/generated-HelloWorld-aaa111.js" defer></script>' in html


def test_render_generated_store_assets_uses_generated_entrypoint(
    settings,
    tmp_project,
    sample_manifest_data,
):
    settings.BASE_DIR = str(tmp_project)
    settings.DEBUG = True
    settings.RSPACK = {}
    _write_manifest(tmp_project, sample_manifest_data)

    html = render_generated_store_assets("helloWorldStore", async_attr=True, defer=False)

    assert "<link " not in html
    assert '<script src="/packs/generated-helloWorldStore-bbb222.js" async></script>' in html
