from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("REACT_ON_DJANGO_SECRET_KEY", "react-on-django-example")
DEBUG = _env_flag("REACT_ON_DJANGO_DEBUG", True)
RSPACK_ENV = os.environ.get("RSPACK_ENV") or ("development" if DEBUG else "production")
RSPACK_OUTPUT_DIR = "packs-test" if RSPACK_ENV == "test" else "packs"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("REACT_ON_DJANGO_ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]
USE_I18N = True
LANGUAGE_CODE = "en-us"
ROOT_URLCONF = "react_on_django_example.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django_rspack",
    "react_on_django",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "react_on_django.middleware.ReactOnDjangoRequestMiddleware",
]
if _env_flag("REACT_ON_DJANGO_USE_RSPACK_PROXY", DEBUG):
    MIDDLEWARE.insert(0, "django_rspack.middleware.RspackDevServerMiddleware")

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "react_on_django.context_processors.react_on_django",
            ],
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = os.environ.get("REACT_ON_DJANGO_STATIC_URL", "/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"

REACT_ON_DJANGO = {
    "bundle_name": os.environ.get("REACT_ON_DJANGO_BUNDLE_NAME", "application"),
    "random_dom_id": _env_flag("REACT_ON_DJANGO_RANDOM_DOM_ID", False),
    "ror_pro": _env_flag("REACT_ON_DJANGO_ROR_PRO", True),
    "rendering_server_url": os.environ.get(
        "REACT_ON_DJANGO_RENDERING_SERVER_URL",
        "http://127.0.0.1:3800",
    ),
    "rendering_server_password": os.environ.get(
        "REACT_ON_DJANGO_RENDERING_SERVER_PASSWORD",
        "react-on-django-example",
    ),
    "server_bundle_js_file": os.environ.get(
        "REACT_ON_DJANGO_SERVER_BUNDLE_JS_FILE",
        "server-bundle.js",
    ),
    "rsc_bundle_js_file": os.environ.get(
        "REACT_ON_DJANGO_RSC_BUNDLE_JS_FILE",
        "rsc-bundle.js",
    ),
    "rsc_payload_generation_url_path": os.environ.get(
        "REACT_ON_DJANGO_RSC_PAYLOAD_PATH",
        "/react_on_django/rsc/",
    ),
    "react_client_manifest_file": os.environ.get(
        "REACT_ON_DJANGO_REACT_CLIENT_MANIFEST_FILE",
        "react-client-manifest.json",
    ),
    "react_server_client_manifest_file": os.environ.get(
        "REACT_ON_DJANGO_REACT_SERVER_CLIENT_MANIFEST_FILE",
        "react-server-client-manifest.json",
    ),
}

RSPACK = {
    "public_output_path": RSPACK_OUTPUT_DIR,
    "manifest_path": BASE_DIR / "public" / RSPACK_OUTPUT_DIR / "manifest.json",
    "dev_server": {
        "host": os.environ.get("RSPACK_DEV_SERVER_HOST", "127.0.0.1"),
        "port": int(os.environ.get("RSPACK_DEV_SERVER_PORT", "3035")),
        "server": "http",
        "hmr": _env_flag("HMR", False),
    },
}
