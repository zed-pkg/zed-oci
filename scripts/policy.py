#!/usr/bin/env python3
"""Fail-closed static policy checks for the zed-oci source tree."""

from __future__ import annotations

import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCKER = ROOT / "docker"
WORKFLOWS = ROOT / ".github" / "workflows"
SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
ACTION_SHA = re.compile(r"^[0-9a-f]{40}$")


def fail(errors: list[str], path: pathlib.Path, message: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {message}")


def main() -> int:
    errors: list[str] = []
    dockerfiles = sorted(DOCKER.rglob("*Dockerfile"))
    workflows = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))

    if not dockerfiles:
        errors.append("docker/: no Dockerfiles found")
    if not workflows:
        errors.append(".github/workflows/: no workflows found")

    for path in dockerfiles:
        text = path.read_text(encoding="utf-8")
        for number, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if line.startswith("FROM "):
                parts = line.split()
                index = 1
                while index < len(parts) and parts[index].startswith("--"):
                    index += 1
                image = parts[index]
                if image.startswith("${"):
                    continue
                if not SHA256.search(image):
                    fail(errors, path, f"line {number}: base image is not digest-pinned")

        for match in re.finditer(r"zed\s+install(?P<body>.*?)(?:\n\s*\n|\Z)", text, re.DOTALL):
            command = " ".join(match.group(0).split())
            if "--frozen" not in command or "--install-mode copy" not in command:
                fail(errors, path, "every OCI install must be frozen copy mode")

        if re.search(r"COPY\s+--from=.*(?:\.zed-pkg|/root|/home/zed)(?:\s|/)", text):
            fail(errors, path, "stage copy may include Zed home, cache, or store")

    for path in workflows:
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            image_input = re.search(
                r"^\s+(?:image|driver-opts|sbom):\s*([^\s#]+)", raw
            )
            if image_input and (
                "image=" in raw
                or "generator=" in raw
                or raw.lstrip().startswith("image:")
            ):
                if "${{" not in raw and not SHA256.search(raw):
                    fail(errors, path, f"line {number}: workflow image is not digest-pinned")

            match = re.search(r"\buses:\s*([^\s#]+)", raw)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if reference.startswith("docker://"):
                if not SHA256.search(reference):
                    fail(errors, path, f"line {number}: Docker action is not digest-pinned")
                continue
            if "@" not in reference or not ACTION_SHA.fullmatch(reference.rsplit("@", 1)[1]):
                fail(errors, path, f"line {number}: action is not pinned by full commit SHA")

    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for required in [".git", ".env", "**/.env.*", "*.pem", "*.key"]:
        if required not in dockerignore:
            errors.append(f".dockerignore: missing sensitive-context rule {required!r}")

    if errors:
        print("zed-oci policy violations:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"policy: verified {len(dockerfiles)} Dockerfiles and "
        f"{len(workflows)} workflows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
