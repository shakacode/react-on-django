import pytest
from django.test import RequestFactory

from react_on_django.conf import reload_react_on_django_settings


@pytest.fixture(autouse=True)
def _reset_cached_settings():
    reload_react_on_django_settings()
    yield
    reload_react_on_django_settings()


@pytest.fixture
def rf():
    return RequestFactory()
