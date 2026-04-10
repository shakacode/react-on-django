# Installation

Install the package and its Django integration dependencies:

```bash
python -m pip install react-on-django django-rspack
```

Add the apps to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django_rspack",
    "react_on_django",
]
```

Add the request middleware so the current request is available to the render
helpers:

```python
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "react_on_django.middleware.ReactOnDjangoRequestMiddleware",
]
```

Configure the bundler manifest and React on Django settings:

```python
RSPACK = {
    "manifest_path": BASE_DIR / "public" / "packs" / "manifest.json",
}

REACT_ON_DJANGO = {
    "bundle_name": "application",
    "server_bundle_js_file": "server-bundle.js",
    "rsc_bundle_js_file": "rsc-bundle.js",
    "rendering_server_url": "http://localhost:3500",
}
```

Finally, load the assets in your base template:

```django
{% load react %}
{% react_component_assets %}
```
