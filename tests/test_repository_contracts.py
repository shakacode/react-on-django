from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_markdown_docs_do_not_reference_local_workspace_paths():
    markdown_files = [
        REPO_ROOT / "README.md",
        *sorted((REPO_ROOT / "docs").rglob("*.md")),
    ]

    offending_links: list[str] = []
    local_link_pattern = re.compile(r"\]\((?:/Users/|file://)")

    for path in markdown_files:
        text = path.read_text()
        if local_link_pattern.search(text):
            offending_links.append(str(path.relative_to(REPO_ROOT)))

    assert offending_links == []


def test_trigger_docs_workflow_keeps_expected_dispatch_contract():
    workflow_path = REPO_ROOT / ".github" / "workflows" / "trigger-docs-site.yml"
    workflow = workflow_path.read_text()

    assert 'paths: ["docs/**"]' in workflow
    assert "workflow_dispatch:" in workflow
    assert "repo_url:" in workflow
    assert "ref:" in workflow
    assert "repositories: react-on-django.com" in workflow
    assert "event-type: docs-updated" in workflow
    assert "github.event.inputs.repo_url" in workflow
    assert "github.event.inputs.ref" in workflow
