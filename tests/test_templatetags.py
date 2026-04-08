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


def test_react_component_hash_supports_as_assignment(settings, rf):
    settings.REACT_ON_DJANGO = {"random_dom_id": False}
    template = Template(
        "{% load react %}"
        '{% react_component_hash "HelloWorld" props=hello_props as component_data %}'
        "{{ component_data.html }}||{{ component_data.script }}"
    )
    context = Context(
        {
            "request": rf.get("/"),
            "hello_props": {"name": "Ada"},
        }
    )

    rendered = template.render(context)

    assert '<div id="HelloWorld-react-component"></div>' in rendered
    assert 'data-component-name="HelloWorld"' in rendered
    assert 'js-react-on-rails-context' in rendered
