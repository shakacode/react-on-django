# React on Django

React on Django renders React components from Django templates with a Python
integration layer that stays compatible with the shared React on Rails
JavaScript runtime.

This initial scaffold covers:

- package metadata and tooling
- Django settings-backed configuration
- safe JSON and HTML output helpers
- client-only component rendering
- Django template tags for `react_component` and `react_component_hash`
- pytest coverage for the initial API surface

`django-rspack` is intentionally kept at the boundary for now. The rendering
core does not assume a specific asset loader yet, so we can plug in the bundler
without rewriting the component API.
