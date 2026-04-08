from __future__ import annotations

from react_on_django.utils.html_output import (
    render_component_spec_script,
    render_context_script,
    render_dom_container,
)


def test_render_dom_container_supports_custom_tag_and_html_options():
    html = render_dom_container(
        dom_id="hello-world-react-component",
        html_options={"tag": "section", "class": "hello-world", "data-controller": "react"},
    )

    assert html == (
        '<section class="hello-world" data-controller="react" '
        'id="hello-world-react-component"></section>'
    )


def test_render_component_spec_script_uses_shared_dom_contract():
    html = render_component_spec_script(
        component_name="HelloWorld",
        dom_id="hello-world-react-component",
        props_json='{"name":"Ada"}',
        trace=True,
    )

    assert 'class="js-react-on-rails-component"' in html
    assert 'id="js-react-on-rails-component-hello-world-react-component"' in html
    assert 'data-component-name="HelloWorld"' in html
    assert 'data-dom-id="hello-world-react-component"' in html
    assert 'data-trace="true"' in html
    assert html.endswith('>{"name":"Ada"}</script>')


def test_render_context_script_outputs_comment_and_context_payload():
    html = render_context_script({"railsEnv": "development", "serverSide": False})

    assert "Powered by React on Django" in html
    assert 'id="js-react-on-rails-context"' in html
    assert '"railsEnv":"development"' in html
