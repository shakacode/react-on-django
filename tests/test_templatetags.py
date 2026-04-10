from __future__ import annotations

from django.template import Context, Template


def test_react_component_template_tag_renders_once_with_single_context_script(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    template = Template(
        "{% load react %}"
        '{% react_component "HelloWorld" props=first_props %}'
        '{% react_component "GoodbyeWorld" props=second_props %}'
    )
    context = Context(
        {
            "request": rf.get("/"),
            "first_props": {"name": "Ada"},
            "second_props": {"name": "Grace"},
        }
    )

    rendered = template.render(context)

    assert rendered.count("js-react-on-rails-context") == 1
    assert rendered.count('class="js-react-on-rails-component"') == 2
    assert '{"name":"Ada"}' in rendered
    assert '{"name":"Grace"}' in rendered


def test_react_context_tag_only_emits_once(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    template = Template(
        "{% load react %}"
        "{% react_context %}"
        '{% react_component "HelloWorld" props=hello_props %}'
    )
    context = Context(
        {
            "request": rf.get("/"),
            "hello_props": {"name": "Ada"},
        }
    )

    rendered = template.render(context)

    assert rendered.count("js-react-on-rails-context") == 1


def test_react_component_hash_supports_as_assignment(settings, rf, monkeypatch):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}

    class FakeServerRenderer:
        def render(self, options, *, include_context_script):
            assert options.prerender is True
            return type(
                "FakeMarkup",
                (),
                {
                    "markup": '<div id="HelloWorld-react-component">SSR</div>',
                    "html": '<div id="HelloWorld-react-component">SSR</div>',
                    "script": (
                        '<script id="js-react-on-rails-context" type="application/json">{}</script>'
                        '<script data-component-name="HelloWorld"></script>'
                    ),
                    "dom_id": options.dom_id,
                    "component_name": options.component_name,
                    "props_json": options.props_json,
                    "extra": {"title": "<title>Ada</title>"},
                },
            )()

    monkeypatch.setattr("react_on_django.component.ServerRenderer", lambda: FakeServerRenderer())

    template = Template(
        "{% load react %}"
        '{% react_component_hash "HelloWorld" props=hello_props as component_data %}'
        "{{ component_data.html|safe }}||{{ component_data.script|safe }}"
    )
    context = Context(
        {
            "request": rf.get("/"),
            "hello_props": {"name": "Ada"},
        }
    )

    rendered = template.render(context)

    assert '<div id="HelloWorld-react-component">SSR</div>' in rendered
    assert 'data-component-name="HelloWorld"' in rendered
    assert "js-react-on-rails-context" in rendered


def test_react_redux_store_tags_render_and_defer(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    template = Template(
        "{% load react %}"
        '{% react_redux_store "helloWorldStore" props=hello_props '
        'defer=True immediate_hydration=True %}'
        "{% react_redux_store_hydration_data %}"
    )
    context = Context(
        {
            "request": rf.get("/"),
            "hello_props": {"helloWorldData": {"name": "Ada"}},
        }
    )

    rendered = template.render(context)

    assert rendered.count("js-react-on-rails-context") == 1
    assert 'data-js-react-on-rails-store="helloWorldStore"' in rendered
    assert 'data-immediate-hydration="true"' in rendered
    assert "reactOnRailsStoreLoaded" in rendered


def test_react_server_render_js_tag(settings, rf, monkeypatch):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
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
                "console_replay_script": "",
                "has_errors": False,
            },
        )(),
    )

    template = Template(
        "{% load react %}"
        "{% react_server_render_js js_expression %}"
    )
    context = Context(
        {
            "request": rf.get("/"),
            "js_expression": "'<strong>SSR JS</strong>'",
        }
    )

    rendered = template.render(context)

    assert "<strong>SSR JS</strong>" in rendered
