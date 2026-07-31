import importlib.util
import sys
from contextlib import contextmanager
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


def test_changelog_has_section_ignores_nested_version_like_headers(tmp_path, monkeypatch):
    release = load_release_module()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n"
        "## [0.1.0a1] - 2026-04-19\n"
        "### [0.1.0] is not a release boundary\n"
        "- This is still part of the alpha notes.\n"
    )
    monkeypatch.setattr(release, "CHANGELOG_FILE", changelog)

    assert release.extract_changelog_section(release.parse_version("0.1.0a1")) == (
        "### [0.1.0] is not a release boundary\n"
        "- This is still part of the alpha notes."
    )


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
    example_test = next(command for command in commands if command[0] == ["./bin/test-ci"])

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


def test_prepared_version_restores_after_pre_commit_failure(tmp_path, monkeypatch):
    release = load_release_module()
    version_file = tmp_path / "__about__.py"
    version_file.write_text('__version__ = "0.1.0"\n')
    monkeypatch.setattr(release, "VERSION_FILE", version_file)

    with pytest.raises(RuntimeError, match="pre-commit failure"):
        with release.prepared_version(
            release.parse_version("0.1.0a1"), restore_after_success=False
        ):
            raise RuntimeError("pre-commit failure")

    assert version_file.read_text() == '__version__ = "0.1.0"\n'


def test_prepared_version_restores_after_keyboard_interrupt(tmp_path, monkeypatch):
    release = load_release_module()
    version_file = tmp_path / "__about__.py"
    version_file.write_text('__version__ = "0.1.0"\n')
    monkeypatch.setattr(release, "VERSION_FILE", version_file)

    with pytest.raises(KeyboardInterrupt):
        with release.prepared_version(
            release.parse_version("0.1.0a1"), restore_after_success=False
        ):
            raise KeyboardInterrupt()

    assert version_file.read_text() == '__version__ = "0.1.0"\n'


def test_prepared_version_keeps_target_version_after_success(tmp_path, monkeypatch):
    release = load_release_module()
    version_file = tmp_path / "__about__.py"
    version_file.write_text('__version__ = "0.1.0"\n')
    monkeypatch.setattr(release, "VERSION_FILE", version_file)

    with release.prepared_version(release.parse_version("0.1.0a1"), restore_after_success=False):
        pass

    assert version_file.read_text() == '__version__ = "0.1.0a1"\n'


def test_prepared_version_restores_successful_dry_run(tmp_path, monkeypatch):
    release = load_release_module()
    version_file = tmp_path / "__about__.py"
    version_file.write_text('__version__ = "0.1.0"\n')
    monkeypatch.setattr(release, "VERSION_FILE", version_file)

    with release.prepared_version(release.parse_version("0.1.0a1"), restore_after_success=True):
        pass

    assert version_file.read_text() == '__version__ = "0.1.0"\n'


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


def test_resolve_upload_plan_warns_when_dry_run_ignores_repository(capsys):
    release = load_release_module()

    plan = release.resolve_upload_plan("testpypi", dry_run=True, yes=True)

    assert plan.repository is None
    assert plan.source == "dry-run"
    assert (
        "ignoring --repository testpypi because --dry-run does not upload"
        in capsys.readouterr().out
    )


def test_validate_upload_push_plan_rejects_upload_without_push():
    release = load_release_module()
    plan = release.UploadPlan(repository="pypi", source="explicit option")

    with pytest.raises(
        release.ReleaseError,
        match="Cannot upload distributions with --skip-push",
    ):
        release.validate_upload_push_plan(skip_push=True, upload_plan=plan)


def test_main_pushes_release_refs_before_upload(monkeypatch):
    release = load_release_module()
    target = release.parse_version("0.1.0a1")
    current = release.parse_version("0.1.0")
    calls = []

    @contextmanager
    def fake_prepared_version(*args, **kwargs):
        yield

    monkeypatch.setattr(release, "read_current_version", lambda: current)
    monkeypatch.setattr(
        release,
        "resolve_target_version",
        lambda requested, current_version: target,
    )
    monkeypatch.setattr(
        release,
        "validate_repo_state",
        lambda version: release.ReleaseContext(
            branch="release-branch",
            current_version=current,
            target_version=version,
            changelog_dirty=False,
            version_dirty=False,
        ),
    )
    monkeypatch.setattr(
        release,
        "resolve_upload_plan",
        lambda repository, dry_run, yes: release.UploadPlan(
            repository="testpypi", source="explicit option"
        ),
    )
    monkeypatch.setattr(release, "print_release_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(release, "prepared_version", fake_prepared_version)
    monkeypatch.setattr(
        release,
        "run_release_checks",
        lambda skip_checks: calls.append("checks"),
    )
    monkeypatch.setattr(release, "build_distributions", lambda: calls.append("build"))
    monkeypatch.setattr(
        release,
        "stage_and_commit_release_files",
        lambda target_version: calls.append("commit"),
    )
    monkeypatch.setattr(release, "create_tag", lambda target_version: calls.append("tag"))
    monkeypatch.setattr(release, "push_release", lambda branch: calls.append("push"))
    monkeypatch.setattr(
        release,
        "upload_distributions",
        lambda repository: calls.append("upload"),
    )
    monkeypatch.setattr(release, "clean_build_artifacts", lambda: calls.append("clean"))

    exit_code = release.main(["--version", "0.1.0a1", "--repository", "testpypi", "--yes"])

    assert exit_code == 0
    assert calls == ["checks", "build", "commit", "tag", "push", "upload", "clean"]
