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
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
ALLOWED_VARIABLE_BASE = "${ZED_OCI_IMAGE}"
SENSITIVE_CONTEXT_RULES = [
    ".git",
    ".env",
    "**/.env.*",
    ".netrc",
    "**/.netrc",
    ".npmrc",
    "**/.npmrc",
    ".pypirc",
    "**/.pypirc",
    ".git-credentials",
    "**/.git-credentials",
    ".ssh",
    "**/.ssh",
    ".aws",
    "**/.aws",
    ".config/gcloud",
    "**/.config/gcloud",
    ".docker/config.json",
    "**/.docker/config.json",
    ".vault-token",
    "**/.vault-token",
    "*.tfstate",
    "*.tfstate.*",
    "*.pem",
    "*.key",
]


def fail(errors: list[str], path: pathlib.Path, message: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {message}")


def main() -> int:
    errors: list[str] = []
    dockerfiles = sorted(DOCKER.rglob("*Dockerfile"))
    workflows = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    version_path = ROOT / "VERSION"

    version = version_path.read_text(encoding="utf-8").strip()
    if not VERSION.fullmatch(version):
        fail(errors, version_path, "must contain one three-part semantic version")

    if not dockerfiles:
        errors.append("docker/: no Dockerfiles found")
    if not workflows:
        errors.append(".github/workflows/: no workflows found")

    for path in dockerfiles:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# syntax=docker/dockerfile:"):
            fail(errors, path, "Dockerfile frontend syntax must be declared on line 1")
        elif not SHA256.search(lines[0]):
            fail(errors, path, "Dockerfile frontend syntax must be digest-pinned")

        for number, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if line.startswith("FROM "):
                parts = line.split()
                index = 1
                while index < len(parts) and parts[index].startswith("--"):
                    index += 1
                image = parts[index]
                if "$" in image:
                    if image != ALLOWED_VARIABLE_BASE or path.parent.name != "examples":
                        fail(
                            errors,
                            path,
                            f"line {number}: only the local example base "
                            f"{ALLOWED_VARIABLE_BASE!r} may be variable",
                        )
                    continue
                if not SHA256.search(image):
                    fail(errors, path, f"line {number}: base image is not digest-pinned")

            if re.match(r"^ADD\s", line, re.IGNORECASE):
                fail(errors, path, f"line {number}: ADD is forbidden; use explicit verified acquisition")

        if path.parent.name == "examples" and f"ARG ZED_OCI_IMAGE=zed-oci:local" not in text:
            fail(errors, path, "variable example base must default to the local verified image")

        user_lines = [line.strip() for line in lines if line.strip().upper().startswith("USER ")]
        if not user_lines:
            fail(errors, path, "final stage must declare an explicit non-root USER")
        elif user_lines[-1].split(maxsplit=1)[1].lower() in {"0", "0:0", "root"}:
            fail(errors, path, "final stage USER must not be root")

        if "--mount=type=secret" in text or "--mount=type=ssh" in text:
            fail(errors, path, "repository-owned image builds must not consume credentials")

        for match in re.finditer(r"zed\s+install(?P<body>.*?)(?:\n\s*\n|\Z)", text, re.DOTALL):
            command = " ".join(match.group(0).split())
            if "--cli" in command:
                if "--cli-install-mode" in command and "--cli-install-mode copy" not in command:
                    fail(errors, path, "project CLI runtimes must use project-owned copy mode")
            elif "--frozen" not in command or "--install-mode copy" not in command:
                fail(errors, path, "every OCI package install must be frozen copy mode")

        if re.search(r"COPY\s+--from=.*(?:\.zed-pkg|/root|/home/zed)(?:\s|/)", text):
            fail(errors, path, "stage copy may include Zed home, cache, or store")

    canonical = (DOCKER / "Dockerfile").read_text(encoding="utf-8")
    if canonical.count(f"ARG ZED_VERSION=v{version}") != 2:
        fail(
            errors,
            DOCKER / "Dockerfile",
            f"both build stages must default to VERSION v{version}",
        )
    for required in [
        'test "$(tar -tzf "/tmp/${archive}")" = "zed"',
        "RUN --network=none set -eux;",
        "--no-create-home",
        'USER 10001:10001',
        'org.opencontainers.image.base.digest="sha256:',
    ]:
        if required not in canonical:
            fail(errors, DOCKER / "Dockerfile", f"missing hardened image contract {required!r}")

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

    publish = (WORKFLOWS / "publish.yml").read_text(encoding="utf-8")
    for required in [
        "id-token: write",
        "provenance: mode=max",
        "sbom: generator=",
        "cosign sign --yes",
        "cosign verify",
        '"attestation-manifest"',
        '"https://slsa.dev/provenance/v1"',
        '"https://spdx.dev/Document"',
    ]:
        if required not in publish:
            fail(errors, WORKFLOWS / "publish.yml", f"missing publication control {required!r}")

    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    for required in [
        "aquasecurity/trivy-action@",
        "ignore-unfixed: true",
        "severity: CRITICAL,HIGH",
        "scanners: vuln",
    ]:
        if required not in ci:
            fail(errors, WORKFLOWS / "ci.yml", f"missing vulnerability control {required!r}")

    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for required in SENSITIVE_CONTEXT_RULES:
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
