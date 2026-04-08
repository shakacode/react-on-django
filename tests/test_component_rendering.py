from __future__ import annotations

from react_on_django.component import (
    ComponentMarkup,
    render_react_component,
    render_react_component_hash,
)


def test_render_react_component_outputs_context_container_and_spec_script(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    request = rf.get("/products?category=tools", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    markup = render_react_component("HelloWorld", props={"name": "Ada"}, request=request)

    assert "js-react-on-rails-context" in markup
    assert '<div id="HelloWorld-react-component"></div>' in markup
    assert 'data-component-name="HelloWorld"' in markup
    assert 'data-dom-id="HelloWorld-react-component"' in markup
    assert '{"name":"Ada"}' in markup


def test_render_react_component_hash_returns_structured_markup(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    request = rf.get("/")

    component = render_react_component_hash("HelloWorld", props={"name": "Ada"}, request=request)

    assert isinstance(component, ComponentMarkup)
    assert component.dom_id == "HelloWorld-react-component"
    assert component.html == '<div id="HelloWorld-react-component"></div>'
    assert 'data-component-name="HelloWorld"' in component.script
    assert component["props_json"] == '{"name":"Ada"}'


def test_render_react_component_uses_random_dom_id_by_default(rf, monkeypatch):
    monkeypatch.setattr("react_on_django.component.uuid.uuid4", lambda: "fixed-uuid")
    request = rf.get("/")

    markup = render_react_component("HelloWorld", props={"name": "Ada"}, request=request)

    assert 'id="HelloWorld-react-component-fixed-uuid"' in markup
