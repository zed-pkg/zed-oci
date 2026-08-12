# zed-oci

Auditable OCI builder images for the independent
[`zed-pkg`](https://github.com/zed-pkg) package manager. This project is not
related to the Zed editor.

`zed` can initialize a package workspace, install project-owned CLI runtimes,
and materialize the exact dependency graph pinned by `.zpkg.lock`. `zed-oci`
puts that installer in a small, multi-architecture builder image so an
application can use Zed during a build and copy only the resulting workspace
into its runtime image.

The canonical repository is named `zed-oci` because the contract is useful to
Docker, Podman, Buildah, Kaniko, and other OCI tooling. Docker-specific assets
live in [`docker/`](docker/).

## The multi-stage pattern

Docker's syntax is a named builder stage followed by `COPY --from`; there is no
`FROM ... --copy` instruction.

```dockerfile
# Replace the version tag with the published digest for production builds.
FROM ghcr.io/zed-pkg/zed-oci:0.2.0 AS zed-builder

WORKDIR /workspace
RUN zed init project --org example

WORKDIR /workspace/project
RUN zed install --cli nodejs
RUN zed install --cli python3

FROM debian:bookworm-slim@sha256:abd67ffcfa541b485a3dff59865ab629aa048a6c613e639d36e7456b0b229241
WORKDIR /app
COPY --from=zed-builder /workspace/project/ /app/
ENV PATH="/app/.zed/tools/bin:${PATH}"
```

The final project contains locked Node.js and Python runtime roots under
`.zed/tools`. Their command links are relative and project-owned, so the final
stage does not need the `zed` executable or `/home/zed/.zed-pkg`. The initial
catalog exposes `node`/`nodejs`, `npm`, `npx`, `corepack`, `python`/`python3`,
and `pip`/`pip3` on both amd64 and arm64 GNU/Linux.

The builder runs as UID/GID `10001:10001` by default, owns `/workspace`, and
uses `/home/zed/.zed-pkg` as `ZED_PKG_HOME`.

For a root-only build step, make the change explicit and align the cache path:

```dockerfile
FROM ghcr.io/zed-pkg/zed-oci:0.2.0 AS dependencies
USER root
ENV HOME=/root ZED_PKG_HOME=/root/.zed-pkg
WORKDIR /app
COPY .zpkg.toml .zpkg.lock ./
RUN --mount=type=cache,target=/root/.zed-pkg \
    zed install --frozen --install-mode copy
```

For the preferred non-root form:

```dockerfile
FROM ghcr.io/zed-pkg/zed-oci:0.2.0 AS dependencies
WORKDIR /workspace
COPY --chown=10001:10001 .zpkg.toml .zpkg.lock ./
RUN --mount=type=cache,target=/home/zed/.zed-pkg,uid=10001,gid=10001 \
    zed install --frozen --install-mode copy
```

See [`docker/examples/cli-tools.Dockerfile`](docker/examples/cli-tools.Dockerfile)
for the executable Node/Python acceptance path,
[`docker/examples/frozen-install.Dockerfile`](docker/examples/frozen-install.Dockerfile)
for a locked package-dependency recipe, and
[`docker/examples/init.Dockerfile`](docker/examples/init.Dockerfile) for the
project-directory initialization canary used by CI.

## Why copy mode matters

Zed's default local-development install uses links into its content-addressed
store. Those links intentionally require the store to remain available.
Container stages, exported filesystems, deployment bundles, and read-only
runtimes need independently owned bytes instead:

```console
zed install --frozen --install-mode copy
```

Copy mode materializes the package files, adapter trees, and hoisted
executables inside the project. The final stage can copy `/app` or `/workspace`
without also carrying the Zed store, download/build cache, credentials, or the
`zed` executable. Hardlinks are not part of the portable contract.

`zed install --cli` uses the same ownership rule automatically. It records
exact upstream URLs, sizes, SHA-256 values, and amd64/arm64 variants in
`.zed/environment.lock.toml`, then copies complete runtime roots into
`.zed/tools`. Run with `--frozen` when replaying a committed environment lock;
run without it when intentionally authoring or updating that lock.

The underlying behavior is specified and tested in:

- [DEN-588: copy-mode Docker/OCI contract](https://linear.app/denman/issue/DEN-588/adopt-copy-mode-as-the-dockeroci-install-contract-and-keep-hardlinks)
- [DEN-591: cross-container canaries](https://linear.app/denman/issue/DEN-591/prove-copy-symlink-docker-and-oci-install-boundaries-with-zed-pkg-test)
- [zed-cli install-mode documentation](https://github.com/zed-pkg/zed-cli/blob/main/docs/install-modes.md)
- [zed-cli project-owned CLI runtime documentation](https://github.com/zed-pkg/zed-cli/blob/main/docs/cli-tools.md)

## Runtime compatibility is still your contract

Multi-stage copying removes Zed itself; it does not make every dependency
universally portable. A final image must still provide the ABI, dynamic
libraries, certificates, locale data, interpreters, and other runtime data the
application and installed tools require. In particular:

- do not copy glibc-linked binaries into a musl-only runtime without proving
  compatibility;
- do not copy architecture-specific output into a different architecture;
- use a compatible distro/runtime stage for dynamic applications;
- use `scratch` or distroless only for verified static outputs with an explicit
  runtime-data inventory.

Zed guarantees a self-contained *installed project tree* in copy mode, not an
automatic ABI conversion.

## Image contents and tags

The image contains:

- Debian bookworm-slim pinned by OCI index digest, providing the glibc ABI used
  by the initial project-owned Node.js and Python catalog;
- a SHA-256-verified `zed` Linux musl release binary;
- an unprivileged `zed` user (`10001:10001`);
- writable `/workspace` and `/home/zed/.zed-pkg` directories;
- OCI source, revision, version, license, and base-image labels.

It deliberately has no application entrypoint. Its default command is
`zed --help`, which makes an accidental standalone run useful without changing
how derived images execute commands.

Release tags mirror this repository's releases. `0.2.0` embeds Zed CLI
`v0.2.0`. Production Dockerfiles should pin the published OCI index digest in
addition to the human-readable tag. Default-branch builds also publish `edge`
and immutable `sha-<commit>` tags.

## Build and verify locally

Docker with BuildKit/buildx is the reference development path:

```console
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --file docker/Dockerfile \
  --output type=oci,dest=zed-oci.tar \
  .

./scripts/verify.sh
```

`./scripts/verify.sh` first enforces static supply-chain and example-policy
rules, then builds the native-platform image, checks the default non-root
identity, runs `zed --version`, and proves both a generated workspace and its
executable Node/Python runtimes cross into a final stage that has neither `zed`
nor `ZED_PKG_HOME`.

Use `NO_DOCKER=1 ./scripts/verify.sh` only when a container runtime is
unavailable. That is a partial check, not container acceptance.

## Publication

Pull requests and pushes run per-platform builder and multi-stage smoke tests.
Pushes to `main` and `v*` tags publish to
`ghcr.io/zed-pkg/zed-oci` with BuildKit provenance and an SBOM. The workflow
then pulls the exact published digest back on both supported platforms and
reruns the identity and CLI smoke checks.

Implementation and publication evidence is tracked in
[DEN-3565](https://linear.app/denman/issue/DEN-3565/zed-oci-publish-zpkg-builder-images-for-auditable-multi-stage).
