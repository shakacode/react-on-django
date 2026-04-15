#!/usr/bin/env python3

from __future__ import annotations

import argparse
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch an example stack command, wait for it to boot, and probe URLs.",
    )
    parser.add_argument("--cwd", default=".", help="Working directory for the stack command.")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL to wait for and probe, for example http://127.0.0.1:3100.",
    )
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        default=[],
        help="URL path to probe after the stack is ready. May be passed multiple times.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Seconds to wait for the stack to become ready.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to launch after '--', for example -- ./bin/dev static --port=3110",
    )
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("Pass the stack command after '--'.")
    if not args.paths:
        args.paths = ["/"]
    return args


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:
        if response.status >= 400:
            raise RuntimeError(f"GET {url} returned status {response.status}")
        return response.read().decode("utf-8", errors="replace")


def terminate_process(process: subprocess.Popen[str]) -> int:
    if process.poll() is not None:
        return int(process.returncode or 0)

    process.send_signal(signal.SIGTERM)
    try:
        return process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=5)


def wait_for_success(
    *,
    url: str,
    process: subprocess.Popen[str],
    timeout: float,
    command: str,
) -> str:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Stack command exited early with code {process.returncode}: {command}"
            )
        try:
            return fetch(url)
        except (urllib.error.URLError, RuntimeError) as exc:
            last_error = exc
            time.sleep(1)

    raise TimeoutError(f"Timed out waiting for {url}: {last_error}")


def main() -> int:
    args = parse_args()
    process = subprocess.Popen(
        args.command,
        cwd=Path(args.cwd).resolve(),
        text=True,
    )

    try:
        ready_url = f"{args.base_url.rstrip('/')}{args.paths[0]}"
        command = " ".join(args.command)

        wait_for_success(
            url=ready_url,
            process=process,
            timeout=args.timeout,
            command=command,
        )

        for path in args.paths:
            wait_for_success(
                url=f"{args.base_url.rstrip('/')}{path}",
                process=process,
                timeout=args.timeout,
                command=command,
            )

        return 0
    finally:
        terminate_process(process)


if __name__ == "__main__":
    raise SystemExit(main())
