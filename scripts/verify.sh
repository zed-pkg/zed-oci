#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 scripts/policy.py

if [[ "${NO_DOCKER:-0}" == "1" ]]; then
  echo "verify: static policy passed; Docker checks explicitly skipped" >&2
  exit 0
fi

runtime="${CONTAINER_RUNTIME:-docker}"
if ! command -v "$runtime" >/dev/null 2>&1; then
  echo "verify: container runtime '$runtime' was not found" >&2
  exit 1
fi

platform="${PLATFORM:-linux/$(docker version --format '{{.Server.Arch}}' | sed 's/^x86_64$/amd64/; s/^aarch64$/arm64/')}"
image="${ZED_OCI_IMAGE:-zed-oci:verify}"
runtime_image="zed-oci-init:verify"

"$runtime" buildx build \
  --platform "$platform" \
  --file docker/Dockerfile \
  --tag "$image" \
  --load \
  .

version="$($runtime run --rm --platform "$platform" "$image" zed --version)"
case "$version" in
  "zed-cli 0.1.0") ;;
  *) echo "verify: unexpected Zed version: $version" >&2; exit 1 ;;
esac

# These variables intentionally expand in the container.
# shellcheck disable=SC2016
"$runtime" run --rm --platform "$platform" "$image" sh -euc '
  test "$(id -u)" = 10001
  test "$(id -g)" = 10001
  test "$PWD" = /workspace
  test "$HOME" = /home/zed
  test "$ZED_PKG_HOME" = /home/zed/.zed-pkg
  test -w /workspace
  test -w "$ZED_PKG_HOME"
'

"$runtime" build \
  --platform "$platform" \
  --build-arg "ZED_OCI_IMAGE=$image" \
  --file docker/examples/init.Dockerfile \
  --tag "$runtime_image" \
  .

# These variables intentionally expand in the container.
# shellcheck disable=SC2016
"$runtime" run --rm --platform "$platform" --read-only "$runtime_image" sh -euc '
  test "$(id -u)" != 0
  ! command -v zed
  test ! -e /home/zed/.zed-pkg
  test -s /app/.zpkg.toml
'

echo "verify: $platform builder and clean-runtime smoke tests passed"
