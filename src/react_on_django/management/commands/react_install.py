from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from ..scaffold import resolve_base_dir, starter_files, write_scaffold_file


class Command(BaseCommand):
    help = "Scaffold a minimal React on Django JavaScript layout."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--base-dir",
            default=None,
            help="Project root to scaffold into. Defaults to settings.BASE_DIR.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite starter files if they already exist.",
        )

    def handle(self, *args, **options) -> None:
        base_dir = resolve_base_dir(options["base_dir"])
        created = 0
        skipped = 0

        for relative_path, content in starter_files().items():
            destination = Path(base_dir, relative_path)
            if write_scaffold_file(destination, content, force=options["force"]):
                created += 1
                self.stdout.write(f"created {destination}")
            else:
                skipped += 1
                self.stdout.write(f"skipped {destination}")

        self.stdout.write(
            self.style.SUCCESS(
                f"React on Django starter ready: created={created}, skipped={skipped}"
            )
        )
