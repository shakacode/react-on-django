from __future__ import annotations

from django.core.management.base import BaseCommand

from ..scaffold import (
    component_template,
    normalize_component_name,
    resolve_base_dir,
    rsc_component_template,
    update_bundle_registration,
    write_scaffold_file,
)


class Command(BaseCommand):
    help = "Generate a React or RSC component scaffold and register it in the bundle entrypoints."

    def add_arguments(self, parser) -> None:
        parser.add_argument("name", help="Component name, for example HelloWorldCard.")
        parser.add_argument(
            "--base-dir",
            default=None,
            help="Project root to scaffold into. Defaults to settings.BASE_DIR.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite the component file if it already exists.",
        )
        parser.add_argument(
            "--rsc",
            action="store_true",
            help="Generate a `.server.jsx` RSC component and register it in `rsc-bundle.jsx`.",
        )
        parser.add_argument(
            "--skip-register",
            action="store_true",
            help="Create files only, do not update bundle registration.",
        )

    def handle(self, *args, **options) -> None:
        base_dir = resolve_base_dir(options["base_dir"])
        component_name = normalize_component_name(options["name"])
        is_rsc = options["rsc"]

        if is_rsc:
            component_path = base_dir / "app/javascript/components" / f"{component_name}.server.jsx"
            created = write_scaffold_file(
                component_path,
                rsc_component_template(component_name),
                force=options["force"],
            )
            self.stdout.write(
                f"{'created' if created else 'skipped'} {component_path}"
            )
            if not options["skip_register"]:
                bundle_path = base_dir / "app/javascript/packs/rsc-bundle.jsx"
                import_line = (
                    f'import {component_name} from "../components/{component_name}.server";'
                )
                changed = update_bundle_registration(
                    bundle_path=bundle_path,
                    import_line=import_line,
                    component_name=component_name,
                )
                self.stdout.write(
                    f"{'updated' if changed else 'unchanged'} {bundle_path}"
                )
        else:
            component_path = base_dir / "app/javascript/components" / f"{component_name}.jsx"
            created = write_scaffold_file(
                component_path,
                component_template(component_name),
                force=options["force"],
            )
            self.stdout.write(
                f"{'created' if created else 'skipped'} {component_path}"
            )
            if not options["skip_register"]:
                import_line = f'import {component_name} from "../components/{component_name}";'
                for bundle_name in ("application.jsx", "server-bundle.jsx"):
                    bundle_path = base_dir / "app/javascript/packs" / bundle_name
                    changed = update_bundle_registration(
                        bundle_path=bundle_path,
                        import_line=import_line,
                        component_name=component_name,
                    )
                    self.stdout.write(
                        f"{'updated' if changed else 'unchanged'} {bundle_path}"
                    )

        self.stdout.write(
            self.style.SUCCESS(f"React on Django component scaffolded: {component_name}")
        )
