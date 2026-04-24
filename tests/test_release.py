import importlib.util
import sys
from pathlib import Path

import pytest


def load_release_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "release.py"
    spec = importlib.util.spec_from_file_location("react_on_django_release", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_version_supports_prereleases():
    release = load_release_module()
    parsed = release.parse_version("0.1.0a2")

    assert parsed.major == 0
    assert parsed.minor == 1
    assert parsed.patch == 0
    assert parsed.prerelease_label == "a"
    assert parsed.prerelease_number == 2
    assert parsed.is_prerelease is True


def test_latest_changelog_version_skips_unreleased(tmp_path, monkeypatch):
    release = load_release_module()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [0.1.0a1] - 2026-04-19\n- First alpha.\n"
    )
    monkeypatch.setattr(release, "CHANGELOG_FILE", changelog)

    assert str(release.latest_changelog_version()) == "0.1.0a1"


def test_resolve_target_version_uses_changelog_when_version_not_passed(tmp_path, monkeypatch):
    release = load_release_module()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [0.1.0a1] - 2026-04-19\n- First alpha.\n")
    monkeypatch.setattr(release, "CHANGELOG_FILE", changelog)

    current = release.parse_version("0.0.9")

    assert str(release.resolve_target_version(None, current)) == "0.1.0a1"


def test_resolve_target_version_requires_changelog_or_explicit_version(tmp_path, monkeypatch):
    release = load_release_module()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [Unreleased]\n")
    monkeypatch.setattr(release, "CHANGELOG_FILE", changelog)

    with pytest.raises(
        release.ReleaseError,
        match="CHANGELOG.md does not contain a release header",
    ):
        release.resolve_target_version(None, release.parse_version("0.1.0"))


def test_changelog_has_section_accepts_second_level_headers(tmp_path, monkeypatch):
    release = load_release_module()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [0.1.0a1] - 2026-04-19\n### Added\n- First alpha.\n")
    monkeypatch.setattr(release, "CHANGELOG_FILE", changelog)

    assert release.changelog_has_section(release.parse_version("0.1.0a1")) is True


def test_changelog_has_section_rejects_empty_release_section(tmp_path, monkeypatch):
    release = load_release_module()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [0.1.0a1] - 2026-04-19\n\n## [0.1.0] - 2026-04-20\n- Stable.\n"
    )
    monkeypatch.setattr(release, "CHANGELOG_FILE", changelog)

    assert release.changelog_has_section(release.parse_version("0.1.0a1")) is False


def test_extract_changelog_section_returns_release_notes_only(tmp_path, monkeypatch):
    release = load_release_module()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n"
        "## [0.1.0a2] - 2026-04-20\n"
        "### Fixed\n"
        "- Tightened release checks.\n\n"
        "## [0.1.0a1] - 2026-04-19\n"
        "- First alpha.\n"
    )
    monkeypatch.setattr(release, "CHANGELOG_FILE", changelog)

    assert release.extract_changelog_section(release.parse_version("0.1.0a2")) == (
        "### Fixed\n- Tightened release checks."
    )


def test_git_dirty_paths_preserves_leading_status_spaces(monkeypatch):
    release = load_release_module()
    monkeypatch.setattr(
        release,
        "run",
        lambda *args, **kwargs: " M CHANGELOG.md\n M src/react_on_django/__about__.py\n",
    )

    assert release.git_dirty_paths() == {
        "CHANGELOG.md",
        "src/react_on_django/__about__.py",
    }


def test_release_check_commands_sets_example_python_for_e2e():
    release = load_release_module()

    commands = list(release.release_check_commands(skip_checks=False))
    example_test = commands[-1]

    assert example_test[0] == ["./bin/test-ci"]
    assert example_test[1].name == "example"
    assert example_test[2]["REACT_ON_DJANGO_EXAMPLE_PYTHON"] == release.sys.executable


def test_update_version_file_rewrites_about_module(tmp_path, monkeypatch):
    release = load_release_module()
    version_file = tmp_path / "__about__.py"
    version_file.write_text('__version__ = "0.1.0"\n')
    monkeypatch.setattr(release, "VERSION_FILE", version_file)

    release.update_version_file(release.parse_version("0.1.0a1"))

    assert version_file.read_text() == '__version__ = "0.1.0a1"\n'


def test_version_sort_key_orders_prereleases_before_stable():
    release = load_release_module()
    alpha = release.version_sort_key(release.parse_version("0.1.0a1"))
    beta = release.version_sort_key(release.parse_version("0.1.0b1"))
    rc = release.version_sort_key(release.parse_version("0.1.0rc1"))
    stable = release.version_sort_key(release.parse_version("0.1.0"))

    assert alpha < beta < rc < stable


def test_parse_repository_name_supports_skip_and_indices():
    release = load_release_module()

    assert release.parse_repository_name("skip") is None
    assert release.parse_repository_name("testpypi") == "testpypi"
    assert release.parse_repository_name("pypi") == "pypi"


def test_resolve_upload_plan_defaults_to_skip_when_yes_is_set():
    release = load_release_module()

    plan = release.resolve_upload_plan(None, dry_run=False, yes=True)

    assert plan.repository is None
    assert plan.source == "non-interactive default"
