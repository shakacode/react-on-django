# Testing and Operations

The example app now includes three operational entrypoints:

- `example/bin/test-ci`
- `example/bin/dev`
- `example/bin/prod`

## CI mode

`example/bin/test-ci` does the full example smoke path:

1. build the example assets
2. boot the fake renderer
3. boot the example app under ASGI
4. run Playwright against the live app

Use it locally from the repo root:

```bash
cd example
./bin/test-ci
```

## Dev mode

`example/bin/dev` supports options for the assets pipeline, renderer, and app
server:

```bash
cd example
./bin/dev dev
./bin/dev static
./bin/dev prod
./bin/dev test
./bin/dev dev --port 3100 --renderer-port 3800 --asset-port 3035
PYTHON=/path/to/python ./bin/dev dev
```

Modes:

- `dev`: rspack dev server with HMR and the live node renderer
- `static`: compiled assets served by Django, no dev server
- `prod`: production bundle build plus the live node renderer
- `test`: deterministic CI mode used by `example/bin/test-ci`

`example/bin/dev` first honors `PYTHON_BIN` or `PYTHON`, then falls back to the
repo-local `.venv`, then the current Python interpreter. That keeps local runs
and GitHub Actions aligned without hard-coding one machine path.

## Production-style mode

`example/bin/prod` builds assets, collects static files by default, then boots
the ASGI app with `uvicorn` and `DEBUG=0`.

```bash
cd example
./bin/prod --renderer=node
./bin/prod --renderer=fake --renderer-port=3510
./bin/prod --renderer=none --skip-collectstatic
PYTHON=/path/to/python ./bin/prod --renderer=fake
```

These scripts are intentionally close to the upstream dummy-app pattern, while
staying Django-native.

## Docs site publishing

The canonical docs source lives in `react-on-django/docs`, while the public
site build and deployment live in `shakacode/react-on-django.com`.

- pushes to `main` that touch `docs/**` should trigger `Trigger docs site rebuild`
- that workflow dispatches `docs-updated` to the site repo
- the source workflow can also be run manually with `workflow_dispatch` when you
  need to retrigger the site without landing another docs commit

Common failure modes:

- `Invalid keyData`: `DOCS_DISPATCH_APP_KEY` is not a valid GitHub App PEM key
- Cloudflare auth errors happen in the site repo, not in this source repo
