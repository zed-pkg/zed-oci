# Security policy

Please report suspected vulnerabilities privately through GitHub's security
advisory flow for `zed-pkg/zed-oci`. Do not include credentials, private image
URLs, registry tokens, or exploit details in a public issue.

The image build accepts no credentials. Zed release archives are pinned by
version and verified against repository-owned SHA-256 values before extraction.
Project-owned Node.js and Python archives are likewise selected from the
versioned Zed catalog, downloaded over HTTPS, and verified against exact locked
sizes and SHA-256 values before bounded, traversal-safe extraction.
The GitHub publication workflow uses the repository-scoped `GITHUB_TOKEN` only
for GHCR and does not pass it into the image build.
