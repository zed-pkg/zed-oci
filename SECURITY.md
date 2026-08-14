# Security policy

Please report suspected vulnerabilities privately through GitHub's security
advisory flow for `zed-pkg/zed-oci`. Do not include credentials, private image
URLs, registry tokens, or exploit details in a public issue.

The image build accepts no credentials. Zed release archives are pinned by
version and verified against repository-owned SHA-256 values before extraction.
The verified archive must also contain exactly one regular file named `zed`;
links, extra members, and path-shaped names are rejected before extraction.
Project-owned Node.js and Python archives are likewise selected from the
versioned Zed catalog, downloaded over HTTPS, and verified against exact locked
sizes and SHA-256 values before bounded, traversal-safe extraction.
The GitHub publication workflow uses the repository-scoped `GITHUB_TOKEN` only
for GHCR and does not pass it into the image build. Publication is authorized
only from `main` or the exact `v<VERSION>` tag. The resulting OCI index is
keylessly signed with GitHub's OIDC identity, and publication fails unless the
exact digest can be pulled back with its signature, per-platform SPDX SBOM, and
SLSA provenance intact.

Runtime canaries use the default non-root account with networking disabled, the
root filesystem read-only, all Linux capabilities dropped, and
`no-new-privileges`. A small `noexec,nosuid,nodev` tmpfs at `/tmp` is required
when invoking Zed on a read-only builder because its embedded command-contract
loader creates ephemeral state there. That tmpfs is not copied into final
runtime stages.
