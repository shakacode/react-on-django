from __future__ import annotations

import pytest

from react_on_django.component import (
    rails_context,
    redux_store,
    redux_store_hydration_data,
    render_rails_context,
    render_react_component,
    render_react_component_hash,
    server_render_js,
)
from react_on_django.errors import ReactOnDjangoError


def test_render_react_component_outputs_context_container_and_spec_script(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    request = rf.get("/products?category=tools", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    markup = render_react_component("HelloWorld", props={"name": "Ada"}, request=request)

    assert "js-react-on-rails-context" in markup
    assert '<div id="HelloWorld-react-component"></div>' in markup
    assert 'data-component-name="HelloWorld"' in markup
    assert 'data-dom-id="HelloWorld-react-component"' in markup
    assert '{"name":"Ada"}' in markup


def test_render_react_component_hash_returns_structured_markup(settings, rf, monkeypatch):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}

    class FakeServerRenderer:
        def render(self, options, *, include_context_script):
            assert options.prerender is True
            return type(
                "FakeMarkup",
                (),
                {
                    "markup": '<div id="HelloWorld-react-component">SSR Ada</div>',
                    "html": '<div id="HelloWorld-react-component">SSR Ada</div>',
                    "script": '<script data-component-name="HelloWorld"></script>',
                    "dom_id": options.dom_id,
                    "component_name": options.component_name,
                    "props_json": options.props_json,
                    "extra": {"title": "<title>Ada</title>"},
                },
            )()

    monkeypatch.setattr("react_on_django.component.ServerRenderer", lambda: FakeServerRenderer())

    component = render_react_component_hash(
        "HelloWorld",
        props={"name": "Ada"},
        request=rf.get("/"),
    )

    assert component["dom_id"] == "HelloWorld-react-component"
    assert component["html"] == '<div id="HelloWorld-react-component">SSR Ada</div>'
    assert 'data-component-name="HelloWorld"' in component["script"]
    assert component["props_json"] == '{"name":"Ada"}'
    assert component["componentHtml"] == component["markup"]
    assert component["title"] == "<title>Ada</title>"


def test_render_react_component_uses_random_dom_id_by_default(rf, monkeypatch):
    monkeypatch.setattr("react_on_django.component.uuid.uuid4", lambda: "fixed-uuid")
    request = rf.get("/")

    markup = render_react_component("HelloWorld", props={"name": "Ada"}, request=request)

    assert 'id="HelloWorld-react-component-fixed-uuid"' in markup


def test_render_react_component_normalizes_html_options_and_nested_data(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    request = rf.get("/client_side_hello_world_with_options")

    markup = render_react_component(
        "HelloWorld",
        props={"helloWorldData": {"name": "Ada"}},
        request=request,
        id="my-hello-world-id",
        html_options={
            "class": "my-hello-world-class",
            "data": {"x": 1, "test_id": "hello-world"},
            "aria": {"label": "Greeting"},
        },
    )

    assert 'id="my-hello-world-id"' in markup
    assert 'class="my-hello-world-class"' in markup
    assert 'data-x="1"' in markup
    assert 'data-test-id="hello-world"' in markup
    assert 'aria-label="Greeting"' in markup


def test_render_react_component_uses_streaming_renderer_when_configured(
    settings,
    rf,
    monkeypatch,
):
    settings.REACT_ON_DJANGO = {
        "random_dom_id": False,
        "server_render_method": "streaming",
    }

    class FakeStreamingRenderer:
        def render(self, options, *, include_context_script):
            assert options.server_render_method == "streaming"
            assert include_context_script is True
            return type(
                "FakeMarkup",
                (),
                {
                    "markup": "<div>streaming</div>",
                    "html": "<div>streaming</div>",
                    "script": "",
                    "dom_id": options.dom_id,
                    "component_name": options.component_name,
                    "props_json": options.props_json,
                    "extra": None,
                },
            )()

    monkeypatch.setattr(
        "react_on_django.component.StreamingRenderer",
        lambda: FakeStreamingRenderer(),
    )

    markup = render_react_component(
        "HelloWorld",
        props={"name": "Ada"},
        request=rf.get("/stream"),
        prerender=True,
    )

    assert markup == "<div>streaming</div>"


def test_render_react_component_uses_rsc_renderer_when_configured(
    settings,
    rf,
    monkeypatch,
):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}

    class FakeRSCRenderer:
        def render(self, options, *, include_context_script):
            assert options.server_render_method == "rsc"
            assert include_context_script is True
            return type(
                "FakeMarkup",
                (),
                {
                    "markup": "<div>rsc</div>",
                    "html": "<div>rsc</div>",
                    "script": "",
                    "dom_id": options.dom_id,
                    "component_name": options.component_name,
                    "props_json": options.props_json,
                    "extra": None,
                },
            )()

    monkeypatch.setattr("react_on_django.component.RSCRenderer", lambda: FakeRSCRenderer())

    markup = render_react_component(
        "HelloWorld",
        props={"name": "Ada"},
        request=rf.get("/rsc"),
        prerender=True,
        server_render_method="rsc",
    )

    assert markup == "<div>rsc</div>"


def test_rails_context_matches_runtime_contract(settings, rf):
    settings.REACT_ON_DJANGO = {"ror_pro": True}
    request = rf.get("/products?category=tools", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    context = rails_context(request, server_side=False)

    assert context["serverSide"] is False
    assert context["href"].endswith("/products?category=tools")
    assert context["location"] == "/products?category=tools"
    assert context["httpAcceptLanguage"] == "en-US,en;q=0.9"

    rendered = render_rails_context(request)

    assert 'id="js-react-on-rails-context"' in rendered
    assert '"serverSide":false' in rendered


def test_react_component_hash_requires_object_results(settings, rf, monkeypatch):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}

    class FakeServerRenderer:
        def render(self, options, *, include_context_script):
            return type(
                "FakeMarkup",
                (),
                {
                    "markup": "<div>string result</div>",
                    "html": "<div>string result</div>",
                    "script": "",
                    "dom_id": options.dom_id,
                    "component_name": options.component_name,
                    "props_json": options.props_json,
                    "extra": None,
                },
            )()

    monkeypatch.setattr("react_on_django.component.ServerRenderer", lambda: FakeServerRenderer())

    with pytest.raises(ReactOnDjangoError):
        render_react_component_hash(
            "HelloWorld",
            props={"name": "Ada"},
            request=rf.get("/"),
        )


def test_render_react_component_includes_store_dependencies_and_immediate_hydration(
    settings,
    rf,
):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    request = rf.get("/")

    redux_store("helloWorldStore", props={"helloWorldData": {"name": "Ada"}}, request=request)

    markup = render_react_component(
        "HelloWorld",
        props={"name": "Ada"},
        request=request,
        store_dependencies=("helloWorldStore",),
        immediate_hydration=True,
    )

    assert 'data-store-dependencies="[&quot;helloWorldStore&quot;]"' in markup
    assert 'data-immediate-hydration="true"' in markup
    assert "reactOnRailsComponentLoaded" in markup


def test_redux_store_renders_context_once_and_supports_deferred_output(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    request = rf.get("/")

    immediate_markup = redux_store(
        "helloWorldStore",
        props={"helloWorldData": {"name": "Ada"}},
        request=request,
    )
    redux_store(
        "helloWorldStore",
        props={"helloWorldData": {"name": "Grace"}},
        request=request,
        defer=True,
        immediate_hydration=True,
    )
    deferred_markup = redux_store_hydration_data(request=request)

    assert immediate_markup.count("js-react-on-rails-context") == 1
    assert deferred_markup.count("js-react-on-rails-context") == 0
    assert 'data-js-react-on-rails-store="helloWorldStore"' in immediate_markup
    assert 'data-js-react-on-rails-store="helloWorldStore"' in deferred_markup
    assert 'data-immediate-hydration="true"' in deferred_markup
    assert redux_store_hydration_data(request=request) == ""


def test_server_render_js_replays_console_output(monkeypatch, rf):
    monkeypatch.setattr(
        "react_on_django.component.resolve_renderer_bundle",
        lambda _: "bundle",
    )
    monkeypatch.setattr(
        "react_on_django.component.perform_server_render",
        lambda **_: type(
            "Result",
            (),
            {
                "html": "<strong>SSR JS</strong>",
                "console_replay_script": "console.log('hello');",
                "has_errors": False,
            },
        )(),
    )

    markup = server_render_js("'<strong>SSR JS</strong>'", request=rf.get("/"))

    assert "<strong>SSR JS</strong>" in markup
    assert 'id="consoleReplayLog"' in markup


def test_render_react_component_auto_loads_generated_component_assets(
    settings,
    rf,
    monkeypatch,
):
    settings.REACT_ON_DJANGO = {
        "random_dom_id": False,
        "auto_load_bundle": True,
    }
    monkeypatch.setattr(
        "react_on_django.component._generated_component_assets_html",
        lambda _: '<script src="/packs/generated-HelloWorld-aaa111.js" defer></script>',
    )

    markup = render_react_component(
        "HelloWorld",
        props={"name": "Ada"},
        request=rf.get("/"),
    )

    assert markup.startswith('<script src="/packs/generated-HelloWorld-aaa111.js" defer></script>')
