# Licensing

React on Django is a single source-available product. There is no separate
feature tier for SSR, streaming SSR, or React Server Components.

## Use model

- non-commercial and no-revenue use is free
- commercial production use requires a paid license from ShakaCode
- the same package, docs set, and example app cover all supported features

## Product scope

Client rendering, SSR, streaming SSR, and RSC all belong to the same package.
As more of the upstream helper surface lands in the Django port, those features
will ship in this package rather than a separate add-on.

## Working with the package

You can adopt the feature set incrementally:

1. start with client rendering
2. enable SSR where it improves first paint or SEO
3. add streaming SSR or RSC where the renderer-backed flows are justified

The licensing model depends on how you use the software in production, not on a
package switch or a second documentation surface.

## Questions

See the
[repository license](https://github.com/shakacode/react-on-django/blob/main/LICENSE)
for the repository terms and visit
[react-on-django.com/licensing](https://react-on-django.com/licensing) for
commercial licensing details.
