#!/usr/bin/env python3
"""Verify OCI base provenance labels match the canonical final FROM image."""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "docker" / "Dockerfile"
SHA256 = r"sha256:[0-9a-f]{64}"


def main() -> int:
    text = DOCKERFILE.read_text(encoding="utf-8")
    images: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("FROM "):
            continue
        parts = line.split()
        index = 1
        while index < len(parts) and parts[index].startswith("--"):
            index += 1
        image = parts[index]
        if "$" not in image:
            images.append(image)

    if not images:
        print("base-metadata: canonical Dockerfile has no concrete FROM image", file=sys.stderr)
        return 1

    final_image = images[-1]
    digest_match = re.search(r"@(" + SHA256 + r")$", final_image)
    if not digest_match:
        print("base-metadata: canonical final FROM is not digest-pinned", file=sys.stderr)
        return 1
    from_digest = digest_match.group(1)

    labels = re.findall(
        r'org\.opencontainers\.image\.base\.digest="(' + SHA256 + r')"',
        text,
    )
    if len(labels) != 1:
        print(
            f"base-metadata: expected exactly one OCI base.digest label, found {len(labels)}",
            file=sys.stderr,
        )
        return 1

    if labels[0] != from_digest:
        print(
            "base-metadata: OCI base.digest label does not match final FROM digest\n"
            f"  FROM:  {from_digest}\n"
            f"  label: {labels[0]}",
            file=sys.stderr,
        )
        return 1

    print(f"base-metadata: final FROM and OCI label agree on {from_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
