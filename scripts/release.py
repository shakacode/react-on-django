"""Maintainer release command for react-on-django."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / "src" / "react_on_django" / "__about__.py"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"
UPLOAD_REPOSITORIES = ("testpypi", "pypi")
ALLOWED_DIRTY_PATHS = {
    "CHANGELOG.md",
    "src/react_on_django/__about__.py",
}
VERSION_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:(?P<pre>a|b|rc)(?P<pre_n>\d+))?$"
)
CHANGELOG_HEADER_RE = re.compile(r"^##\s+\[(?P<version>[^\]]+)\](?:\s+-\s+.+)?$")


class ReleaseError(RuntimeError):
    """Raised when the release flow cannot continue safely."""


@dataclass(frozen=True)
class ParsedVersion:
    major: int
    minor: int
    patch: int
    prerelease_label: str | None
    prerelease_number: int | None

    @property
    def is_prerelease(self) -> bool:
        return self.prerelease_label is not None

    @property
    def tag(self) -> str:
        return f"v{self}"

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if not self.is_prerelease:
            return base
        return f"{base}{self.prerelease_label}{self.prerelease_number}"


@dataclass(frozen=True)
class ReleaseContext:
    branch: str
    current_version: ParsedVersion
    target_version: ParsedVersion
    changelog_dirty: bool
    version_dirty: bool


@dataclass(frozen=True)
class UploadPlan:
    repository: str | None
    source: str


def parse_version(value: str) -> ParsedVersion:
    match = VERSION_RE.match(value.strip())
    if not match:
        raise ReleaseError(
            f"Unsupported version {value!r}. Use X.Y.Z, X.Y.ZaN, X.Y.ZbN, or X.Y.ZrcN."
        )

    prerelease_number = match.group("pre_n")
    return ParsedVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease_label=match.group("pre"),
        prerelease_number=int(prerelease_number) if prerelease_number else None,
    )


def version_sort_key(version: ParsedVersion) -> tuple[int, int, int, int, int]:
    stage_rank = {None: 3, "rc": 2, "b": 1, "a": 0}[version.prerelease_label]
    prerelease_number = version.prerelease_number or 0
    return (version.major, version.minor, version.patch, stage_rank, prerelease_number)


def read_current_version() -> ParsedVersion:
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', text, re.M)
    if not match:
        raise ReleaseError(f"Could not find __version__ in {VERSION_FILE}")
    return parse_version(match.group(1))


def update_version_file(target_version: ParsedVersion) -> None:
    text = VERSION_FILE.read_text(encoding="utf-8")
    updated = re.sub(
        r'^__version__ = "([^"]+)"$',
        f'__version__ = "{target_version}"',
        text,
        count=1,
        flags=re.M,
    )
    if updated == text:
        raise ReleaseError(f"Could not update version in {VERSION_FILE}")
    VERSION_FILE.write_text(updated, encoding="utf-8")


@contextmanager
def prepared_version(
    target_version: ParsedVersion, *, restore_after_success: bool
) -> Iterator[None]:
    original = VERSION_FILE.read_text(encoding="utf-8")
    current_version = read_current_version()
    should_update = current_version != target_version

    if should_update:
        update_version_file(target_version)

    success = False
    try:
        yield
        success = True
    finally:
        if should_update and (restore_after_success or not success):
            VERSION_FILE.write_text(original, encoding="utf-8")


def latest_changelog_version() -> ParsedVersion | None:
    if not CHANGELOG_FILE.exists():
        return None

    for line in CHANGELOG_FILE.read_text(encoding="utf-8").splitlines():
        match = CHANGELOG_HEADER_RE.match(line.strip())
        if not match:
            continue

        raw_version = match.group("version").strip()
        if raw_version.lower() == "unreleased":
            continue
        return parse_version(raw_version)

    return None


def extract_changelog_section(version: ParsedVersion) -> str | None:
    if not CHANGELOG_FILE.exists():
        return None

    lines = CHANGELOG_FILE.read_text(encoding="utf-8").splitlines()
    collecting = False
    section_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        match = CHANGELOG_HEADER_RE.match(stripped)
        if match:
            raw_version = match.group("version").strip()
            if collecting:
                break
            if raw_version == str(version):
                collecting = True
            continue

        if collecting:
            section_lines.append(line)

    if not collecting:
        return None

    section = "\n".join(section_lines).strip()
    return section or None


def changelog_has_section(version: ParsedVersion) -> bool:
    return extract_changelog_section(version) is not None


def run(
    *args: str,
    capture_output: bool = False,
    check: bool = True,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
) -> str:
    print(f"$ {shlex.join(args)}", flush=True)
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=False,
        text=True,
        capture_output=capture_output,
        env=env,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr.strip() if completed.stderr else ""
        stdout = completed.stdout.strip() if completed.stdout else ""
        details = "\n".join(part for part in (stdout, stderr) if part)
        message = (
            details or f"Command failed with exit code {completed.returncode}: {shlex.join(args)}"
        )
        raise ReleaseError(message)
    return completed.stdout if capture_output else ""


def git_dirty_paths() -> set[str]:
    output = run("git", "status", "--porcelain=v1", capture_output=True)
    dirty_paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        dirty_paths.add(line[3:])
    return dirty_paths


def current_branch() -> str:
    return run("git", "branch", "--show-current", capture_output=True).strip()


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def resolve_target_version(
    requested_version: str | None, current_version: ParsedVersion
) -> ParsedVersion:
    if requested_version:
        return parse_version(requested_version)

    changelog_version = latest_changelog_version()
    if changelog_version is None:
        raise ReleaseError(
            "CHANGELOG.md does not contain a release header yet. Add one like "
            "`## [0.1.0a1] - 2026-04-19` or pass --version."
        )

    if version_sort_key(changelog_version) < version_sort_key(current_version):
        raise ReleaseError(
            "Latest CHANGELOG version "
            f"{changelog_version} is older than current package version "
            f"{current_version}."
        )

    return changelog_version


def prompt_yes_no(question: str, *, default: bool = False) -> bool:
    if not sys.stdin.isatty():
        return default

    suffix = " [Y/n] " if default else " [y/N] "
    response = input(question + suffix).strip().lower()
    if not response:
        return default
    return response in {"y", "yes"}


def validate_repo_state(target_version: ParsedVersion) -> ReleaseContext:
    branch = current_branch()
    dirty_paths = git_dirty_paths()
    unexpected = sorted(path for path in dirty_paths if path not in ALLOWED_DIRTY_PATHS)
    if unexpected:
        raise ReleaseError(
            "Release requires a clean worktree except for CHANGELOG.md and "
            "src/react_on_django/__about__.py.\nUnexpected changes:\n- " + "\n- ".join(unexpected)
        )

    if not target_version.is_prerelease and branch != "main":
        raise ReleaseError(f"Stable releases must be run from main. Current branch: {branch}")

    if tag_exists(target_version.tag):
        raise ReleaseError(f"Git tag {target_version.tag} already exists.")

    if not changelog_has_section(target_version):
        raise ReleaseError(
            f"CHANGELOG.md is missing a non-empty section for {target_version}. Add a heading like "
            f"`## [{target_version}] - YYYY-MM-DD` and describe the release before releasing."
        )

    current_version = read_current_version()
    return ReleaseContext(
        branch=branch,
        current_version=current_version,
        target_version=target_version,
        changelog_dirty="CHANGELOG.md" in dirty_paths,
        version_dirty="src/react_on_django/__about__.py" in dirty_paths,
    )


def release_check_commands(
    skip_checks: bool,
) -> Iterable[tuple[list[str], Path, dict[str, str] | None]]:
    if skip_checks:
        return ()

    return (
        ([sys.executable, "-m", "ruff", "check", "."], REPO_ROOT, None),
        ([sys.executable, "-m", "pytest"], REPO_ROOT, None),
        (["npm", "ci"], REPO_ROOT / "example", None),
        (
            ["./bin/test-ci"],
            REPO_ROOT / "example",
            {
                **os.environ,
                "REACT_ON_DJANGO_EXAMPLE_PYTHON": sys.executable,
            },
        ),
    )


def run_release_checks(skip_checks: bool) -> None:
    for command, cwd, env in release_check_commands(skip_checks):
        run(*command, cwd=cwd, env=env)


def build_distributions() -> None:
    clean_build_artifacts()
    run(sys.executable, "-m", "build", "--no-isolation")
    dist_dir = REPO_ROOT / "dist"
    artifacts = sorted(str(path) for path in dist_dir.glob("*"))
    if not artifacts:
        raise ReleaseError("python -m build completed without creating dist artifacts.")
    run(sys.executable, "-m", "twine", "check", *artifacts)


def dist_artifacts() -> list[str]:
    artifacts = sorted(str(path) for path in (REPO_ROOT / "dist").glob("*"))
    if not artifacts:
        raise ReleaseError("No distribution artifacts were found in dist/.")
    return artifacts


def clean_build_artifacts() -> None:
    dist_dir = REPO_ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)


def parse_repository_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized or normalized == "skip":
        return None
    if normalized not in UPLOAD_REPOSITORIES:
        allowed = ", ".join(("skip",) + UPLOAD_REPOSITORIES)
        raise ReleaseError(f"Unsupported repository {value!r}. Use one of: {allowed}.")
    return normalized


def prompt_upload_repository() -> UploadPlan:
    if not sys.stdin.isatty():
        return UploadPlan(repository=None, source="non-interactive default")

    prompt = "Upload distributions now? [skip/testpypi/pypi] "
    while True:
        response = input(prompt).strip().lower()
        if not response or response == "skip":
            return UploadPlan(repository=None, source="interactive selection")
        if response in UPLOAD_REPOSITORIES:
            return UploadPlan(repository=response, source="interactive selection")
        print("Enter one of: skip, testpypi, pypi.", flush=True)


def resolve_upload_plan(
    repository: str | None,
    *,
    dry_run: bool,
    yes: bool,
) -> UploadPlan:
    selected = parse_repository_name(repository)
    if dry_run:
        if selected is not None:
            print(
                f"Warning: ignoring --repository {selected} because --dry-run does not upload.",
                flush=True,
            )
        return UploadPlan(repository=None, source="dry-run")
    if selected is not None:
        return UploadPlan(repository=selected, source="explicit option")
    if yes:
        return UploadPlan(repository=None, source="non-interactive default")
    return prompt_upload_repository()


def validate_upload_push_plan(*, skip_push: bool, upload_plan: UploadPlan) -> None:
    if skip_push and upload_plan.repository is not None:
        raise ReleaseError(
            "Cannot upload distributions with --skip-push. Push the release branch and "
            "tag before uploading to pypi or testpypi."
        )


def upload_distributions(repository: str) -> None:
    artifacts = dist_artifacts()
    run(sys.executable, "-m", "twine", "upload", "--repository", repository, *artifacts)


def stage_and_commit_release_files(target_version: ParsedVersion) -> None:
    run("git", "add", "CHANGELOG.md", "src/react_on_django/__about__.py")
    diff_status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO_ROOT,
        check=False,
    )
    if diff_status.returncode == 0:
        return
    run("git", "commit", "-m", f"Release {target_version}")


def create_tag(target_version: ParsedVersion) -> None:
    run("git", "tag", "-a", target_version.tag, "-m", f"react-on-django {target_version.tag}")


def push_release(branch: str) -> None:
    run("git", "push", "origin", branch, "--follow-tags")


def print_release_summary(
    context: ReleaseContext,
    *,
    dry_run: bool,
    skip_checks: bool,
    skip_push: bool,
    upload_plan: UploadPlan,
) -> None:
    print("\nRelease summary", flush=True)
    print(f"  Branch: {context.branch}", flush=True)
    print(f"  Current version: {context.current_version}", flush=True)
    print(f"  Target version: {context.target_version}", flush=True)
    print(f"  Tag: {context.target_version.tag}", flush=True)
    print(
        f"  Type: {'prerelease' if context.target_version.is_prerelease else 'stable'}",
        flush=True,
    )
    checks = "skipped" if skip_checks else "ruff, pytest, example/bin/test-ci, build, twine check"
    print(f"  Checks: {checks}", flush=True)
    upload = upload_plan.repository or "skip"
    print(f"  Upload: {upload} ({upload_plan.source})", flush=True)
    print(f"  Push: {'skipped' if skip_push else 'origin + tag'}", flush=True)
    print(f"  Mode: {'dry-run' if dry_run else 'live'}", flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Release react-on-django from a clean maintainer checkout."
    )
    parser.add_argument("--version", help="Explicit release version, such as 0.1.0a1.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run checks and build, but do not commit, tag, or push.",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip ruff, pytest, and example test execution.",
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Create the commit and tag locally without pushing.",
    )
    parser.add_argument(
        "--repository",
        choices=("skip",) + UPLOAD_REPOSITORIES,
        help="Optional local upload target: pypi, testpypi, or skip.",
    )
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation prompts.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        requested_version = args.version or os.environ.get("VERSION")
        target_version = resolve_target_version(requested_version, read_current_version())
        context = validate_repo_state(target_version)
        upload_plan = resolve_upload_plan(
            args.repository or os.environ.get("REPOSITORY"),
            dry_run=args.dry_run,
            yes=args.yes,
        )
        validate_upload_push_plan(skip_push=args.skip_push, upload_plan=upload_plan)
        print_release_summary(
            context,
            dry_run=args.dry_run,
            skip_checks=args.skip_checks,
            skip_push=args.skip_push,
            upload_plan=upload_plan,
        )

        if context.target_version.is_prerelease and context.branch != "main":
            if not args.yes and not prompt_yes_no(
                f"Pre-release {context.target_version} will be cut from {context.branch}. Continue?"
            ):
                raise ReleaseError("Aborted before release.")

        if not args.yes and not prompt_yes_no(f"Proceed with release {context.target_version}?"):
            raise ReleaseError("Aborted before release.")

        try:
            with prepared_version(context.target_version, restore_after_success=args.dry_run):
                run_release_checks(args.skip_checks)
                build_distributions()

                if args.dry_run:
                    print("\nDry run completed. No commit, tag, or push was created.", flush=True)
                    return 0

            stage_and_commit_release_files(context.target_version)
            create_tag(context.target_version)
            if not args.skip_push:
                push_release(context.branch)
            if upload_plan.repository is not None:
                upload_distributions(upload_plan.repository)
        finally:
            clean_build_artifacts()

        print("\nRelease command completed.", flush=True)
        if upload_plan.repository is not None:
            print(f"Uploaded distributions to {upload_plan.repository}.", flush=True)
        if args.skip_push:
            print(
                f"Next step: push {context.branch} with {context.target_version.tag} when ready.",
                flush=True,
            )
        elif upload_plan.repository is None:
            print(
                "Next step: run the manual GitHub Release workflow or rerun "
                "with --repository pypi|testpypi if you want local twine upload.",
                flush=True,
            )
        else:
            print(f"Git refs are pushed for {context.target_version.tag}.", flush=True)
        return 0
    except ReleaseError as exc:
        print(f"\n❌ {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
