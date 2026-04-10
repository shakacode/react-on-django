import pytest
from django.test import RequestFactory
from django_rspack.conf import reset_config
from django_rspack.manifest import reset_manifest

from react_on_django.conf import reload_react_on_django_settings
from react_on_django.middleware import reset_helper_state


@pytest.fixture(autouse=True)
def _reset_cached_settings():
    reload_react_on_django_settings()
    reset_helper_state()
    reset_config()
    reset_manifest()
    yield
    reload_react_on_django_settings()
    reset_helper_state()
    reset_config()
    reset_manifest()


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / "public" / "packs").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_manifest_data():
    return {
        "application.js": "/packs/application-abc123.js",
        "application.css": "/packs/application-def456.css",
        "generated/HelloWorld.js": "/packs/generated-HelloWorld-aaa111.js",
        "generated/HelloWorld.css": "/packs/generated-HelloWorld-aaa111.css",
        "generated/helloWorldStore.js": "/packs/generated-helloWorldStore-bbb222.js",
        "server-bundle.js": "/packs/server-bundle-xyz789.js",
        "rsc-bundle.js": "/packs/rsc-bundle.js",
        "entrypoints": {
            "application": {
                "assets": {
                    "js": [
                        "/packs/runtime-abc123.js",
                        "/packs/vendor-789xyz.js",
                        "/packs/application-abc123.js",
                    ],
                    "css": ["/packs/application-def456.css"],
                }
            },
            "generated/HelloWorld": {
                "assets": {
                    "js": ["/packs/generated-HelloWorld-aaa111.js"],
                    "css": ["/packs/generated-HelloWorld-aaa111.css"],
                }
            },
            "generated/helloWorldStore": {
                "assets": {
                    "js": ["/packs/generated-helloWorldStore-bbb222.js"],
                    "css": [],
                }
            },
        },
    }
