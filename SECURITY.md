# Security policy

Please report suspected vulnerabilities privately through GitHub's security
advisory flow for `zed-pkg/zed-oci`. Do not include credentials, private image
URLs, registry tokens, or exploit details in a public issue.

The image build accepts no credentials. Zed release archives are pinned by
version and verified against repository-owned SHA-256 values before extraction.
The GitHub publication workflow uses the repository-scoped `GITHUB_TOKEN` only
for GHCR and does not pass it into the image build.
