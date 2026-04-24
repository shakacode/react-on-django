# Releasing react-on-django

The maintainer flow is:

1. Update `CHANGELOG.md` for the version you want to ship.
2. Run `make release`.
3. Confirm the version, branch, checks, upload target, and push step.
4. If you chose `pypi` or `testpypi`, `twine` uploads locally.
5. Otherwise, push the tag and use the GitHub workflow manually if you still
   want CI-based publishing.

`make release` is the Python equivalent of `rake release`. It validates the
repo state, bumps `src/react_on_django/__about__.py` if needed, runs the
release checks, creates the release commit, tags it, optionally uploads with
`twine`, and then pushes the branch plus tag to GitHub.

## Before you run it

Start from a clean maintainer checkout. The release command refuses to run if
the worktree has changes outside:

- `CHANGELOG.md`
- `src/react_on_django/__about__.py`

Install the maintainer dependencies once:

```bash
python -m pip install -e '.[dev]'
```

If your checkout has multiple local Python entrypoints, point `make` at the
interpreter you want:

```bash
make release PYTHON=.venv/bin/python3.14
```

`react-on-django` depends on `django-rspack`, so publish the matching
`django-rspack` release to the same package index before publishing
`react-on-django`. PyPI accepts the upload even if dependencies are missing,
but user installs will fail until `django-rspack>=0.1.0` is available.

## Changelog format

Add a versioned heading for the release you want to cut. The release command
uses the newest versioned heading in `CHANGELOG.md` unless you pass `VERSION=...`
explicitly. The section must contain actual release notes, not just the
heading.

Example:

```md
## [0.1.0a1] - 2026-04-19

### Added

- First alpha release.
```

## Release commands

Normal release:

```bash
make release
```

Explicit version override:

```bash
make release VERSION=0.1.0a1
```

Release and upload to TestPyPI:

```bash
make release VERSION=0.1.0a1 REPOSITORY=testpypi
```

Release and upload to PyPI:

```bash
make release VERSION=0.1.0 REPOSITORY=pypi
```

Dry run without commit, tag, or push:

```bash
make release-dry-run VERSION=0.1.0a1
```

The release command runs:

- `ruff check .`
- `pytest`
- `cd example && npm ci`
- `cd example && ./bin/test-ci`
- `python -m build --no-isolation`
- `python -m twine check dist/*`

Stable releases must run from `main`. Prereleases can run from another branch,
but the command will make you confirm that explicitly.

## Alpha releases

Use standard PEP 440 prerelease versions:

- `0.1.0a1` for the first alpha of `0.1.0`
- `0.1.0a2` for the next alpha
- `0.1.0b1` for the first beta
- `0.1.0rc1` for the first release candidate

`0.10` is not an alpha release. The alpha marker must be part of the version
string, for example `0.10a1` or `0.1.0a1`.

Each prerelease is immutable. If `0.1.0a1` is bad, publish `0.1.0a2` instead of
trying to replace `0.1.0a1`.

For local uploads, PyPI does not use a per-release OTP prompt like RubyGems.
Use a PyPI API token in `$HOME/.pypirc`, keyring, or `TWINE_*` environment
variables instead.

Consumers install prereleases with:

```bash
python -m pip install --pre react-on-django
```

Or pin one directly:

```bash
python -m pip install react-on-django==0.1.0a1
```

## What `make release` actually does

1. Resolves the target version from `VERSION=...` or the newest release heading
   in `CHANGELOG.md`.
2. Verifies the branch, changelog section, worktree cleanliness, and tag
   availability.
3. Updates `src/react_on_django/__about__.py` to the release version.
4. Runs the release checks and local package build.
5. Commits `CHANGELOG.md` and `src/react_on_django/__about__.py` if needed.
6. Creates `vX.Y.Z` or `vX.Y.ZaN`.
7. Optionally uploads `dist/*` with `twine upload --repository pypi|testpypi`.
8. Pushes the current branch plus tags to `origin`.

## Local upload setup

For local `twine` uploads, configure PyPI and TestPyPI credentials once in
`$HOME/.pypirc` or keyring. Example `.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = <PyPI token>

[testpypi]
username = __token__
password = <TestPyPI token>
```

## Optional GitHub workflow setup

`react-on-django` publishes to PyPI through `.github/workflows/release.yml`.
The local release command is now the primary maintainer path. The GitHub
workflow remains available as a manual trusted-publishing fallback.

Configure trusted publishers for the `react-on-django` project:

1. In PyPI, open the project and add a publisher for:
   - owner: `shakacode`
   - repository: `react-on-django`
   - workflow: `.github/workflows/release.yml`
   - environment: `pypi`
2. In TestPyPI, add the same publisher but use the `testpypi` environment.
3. In GitHub, create `pypi` and `testpypi` environments for this repository.
4. Require manual approval on the `pypi` environment before production
   publishes.

Your PyPI account and 2FA are only used for this website-side setup. Once the
trusted publishers are configured, the release workflow publishes through
PyPI's OIDC flow and does not require a password, API token, or one-time code
for each release.
