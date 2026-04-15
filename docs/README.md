# React on Django Docs

This directory is the canonical documentation source for `react-on-django`.

The public site will live in the separate `shakacode/react-on-django.com` repo.
That site should sync content from this directory, prepare it for Docusaurus,
and handle deployment, branding, and marketing pages.

Current docs are organized into:

- `introduction.md`
- `getting-started/`
- `guides/`
- `sidebars.ts`

## Publishing flow

Documentation changes in `docs/**` on `main` should trigger the
`Trigger docs site rebuild` workflow in this repo. That workflow sends a
`docs-updated` repository dispatch event to `shakacode/react-on-django.com`,
which is responsible for syncing this directory, preparing the Docusaurus
content, and deploying the public site.

Operational notes:

- this repo needs `DOCS_DISPATCH_APP_ID` and `DOCS_DISPATCH_APP_KEY` secrets
- the site repo needs its own Cloudflare deploy credentials
- `Trigger docs site rebuild` also supports `workflow_dispatch`, so the docs
  site can be retriggered without landing a new docs commit
