# Agent instructions

## Scope

- These instructions apply to the entire `zed-oci` repository unless a deeper
  `AGENTS.md` narrows them.
- This repository packages the independent `zed-pkg` package manager. It is
  unrelated to the Zed editor.

## OCI contract

- Keep the repository runtime-neutral. Docker-specific files belong under
  `docker/`, while documentation and policy should apply to any OCI builder.
- Treat `zed install --frozen --install-mode copy` as the portable image-layer
  package contract. Treat the default copy mode of `zed install --cli` as the
  project-owned runtime contract. Never rely on store-backed symlinks or
  hardlinks across stages.
- Keep the default builder non-root. Root recipes must set `HOME` and
  `ZED_PKG_HOME` explicitly and return to a non-root runtime where practical.
- Do not copy the Zed store, download/build caches, credentials, or the `zed`
  executable into a final runtime stage unless that runtime explicitly needs
  them.
- Do not claim arbitrary native outputs are portable across incompatible libc,
  distribution, architecture, or system-library boundaries.

## Supply chain and validation

- Pin base images by digest and third-party Actions by full commit SHA.
- Verify downloaded Zed release artifacts against repository-owned SHA-256
  values before extraction.
- Keep build contexts free of credentials, VCS metadata, caches, and local
  environment files.
- Run `./scripts/verify.sh`. Use `NO_DOCKER=1 ./scripts/verify.sh` only for the
  static-policy portion and report that container smoke tests did not run.
- Distinguish a source build from a remotely published GHCR image. Do not call
  publication complete until the exact digest has been pulled back and tested.
