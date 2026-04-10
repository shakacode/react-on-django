from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError

IMPORT_LINE_RE = re.compile(r"^import .+;$", re.MULTILINE)
REGISTER_CALL_RE = re.compile(r"RuntimeBridge\.register\(\{(?P<body>.*?)\}\);", re.DOTALL)


def resolve_base_dir(base_dir: str | None) -> Path:
    return Path(base_dir or settings.BASE_DIR).resolve()


def normalize_component_name(raw_name: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", raw_name) if part]
    if not parts:
        raise CommandError("Component name must contain at least one letter or number.")
    return "".join(part[:1].upper() + part[1:] for part in parts)


def write_scaffold_file(path: Path, content: str, *, force: bool) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return False
    path.write_text(content)
    return True


def update_bundle_registration(
    *,
    bundle_path: Path,
    import_line: str,
    component_name: str,
) -> bool:
    if not bundle_path.exists():
        raise CommandError(
            f"Expected bundle file at {bundle_path}. Run `manage.py react_install` first."
        )

    content = bundle_path.read_text()
    changed = False
    if import_line not in content:
        import_matches = list(IMPORT_LINE_RE.finditer(content))
        if not import_matches:
            raise CommandError(f"Could not find an import block in {bundle_path}.")
        insertion_point = import_matches[-1].end()
        content = f"{content[:insertion_point]}\n{import_line}{content[insertion_point:]}"
        changed = True

    register_match = REGISTER_CALL_RE.search(content)
    if register_match is None:
        raise CommandError(f"Could not find RuntimeBridge.register(...) in {bundle_path}.")

    existing_names = [
        value.strip()
        for value in register_match.group("body").split(",")
        if value.strip()
    ]
    if component_name not in existing_names:
        existing_names.append(component_name)
        replacement = f"RuntimeBridge.register({{ {', '.join(existing_names)} }});"
        content = (
            f"{content[:register_match.start()]}"
            f"{replacement}"
            f"{content[register_match.end():]}"
        )
        changed = True

    if changed:
        bundle_path.write_text(content)
    return changed


def starter_files() -> dict[str, str]:
    return {
        "app/javascript/components/HelloWorld.jsx": """import React, { useState } from "react";

export default function HelloWorld({ helloWorldData }) {
  const [name, setName] = useState(helloWorldData?.name ?? "World");

  return (
    <section className="hello-world">
      <h2>Hello, {name}!</h2>
      <label>
        Name
        <input value={name} onChange={(event) => setName(event.target.value)} />
      </label>
    </section>
  );
}
""",
        "app/javascript/components/RscHelloWorld.server.jsx": (
            """export default function RscHelloWorld({ name }) {
  return <h2>Hello from an RSC payload, {name ?? "World"}!</h2>;
}
"""
        ),
        "app/javascript/packs/application.jsx": (
            """import RuntimeBridge from "react-on-rails-pro/client";

import HelloWorld from "../components/HelloWorld";
import "../styles/application.css";

RuntimeBridge.register({ HelloWorld });
"""
        ),
        "app/javascript/packs/server-bundle.jsx": """import RuntimeBridge from "react-on-rails-pro";

import HelloWorld from "../components/HelloWorld";

RuntimeBridge.register({ HelloWorld });
""",
        "app/javascript/packs/rsc-bundle.jsx": """import RuntimeBridge from "react-on-rails-pro";

import RscHelloWorld from "../components/RscHelloWorld.server";

RuntimeBridge.register({ RscHelloWorld });
""",
        "app/javascript/styles/application.css": """.hello-world {
  font-family: sans-serif;
  max-width: 32rem;
}
""",
    }


def component_template(component_name: str) -> str:
    return f"""export default function {component_name}(props) {{
  return (
    <section data-testid="{component_name}">
      <h2>{component_name}</h2>
      <pre>{{JSON.stringify(props, null, 2)}}</pre>
    </section>
  );
}}
"""


def rsc_component_template(component_name: str) -> str:
    return f"""export default function {component_name}({{ message }}) {{
  return <section data-testid="{component_name}">{{message ?? "{component_name}"}}</section>;
}}
"""
