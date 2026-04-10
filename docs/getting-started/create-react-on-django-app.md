# Create a React on Django App

The package ships with both a reference example in `example/` and starter
management commands.

Recommended starting points:

- run `manage.py react_install` for the starter JavaScript layout
- run `manage.py react_generate` for new component scaffolds
- copy the example bundle layout under `app/javascript/`
- copy the Django settings seam for `django-rspack`
- copy the example process scripts:
  - `example/bin/dev`
  - `example/bin/prod`
  - `example/bin/test-ci`

Minimum directories:

```text
your-project/
  app/javascript/components/
  app/javascript/packs/
  public/packs/manifest.json
  templates/
```

Starter command examples:

```bash
python manage.py react_install
python manage.py react_generate dashboard-card
python manage.py react_generate posts-feed --rsc
```

The example app is still the reference for richer flows such as shared stores,
streaming shells, and the current RSC demos.
