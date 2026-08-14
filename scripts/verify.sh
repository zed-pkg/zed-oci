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

platform="${PLATFORM:-linux/$("$runtime" version --format '{{.Server.Arch}}' | sed 's/^x86_64$/amd64/; s/^aarch64$/arm64/')}"
image="${ZED_OCI_IMAGE:-zed-oci:verify}"
runtime_image="zed-oci-init:verify"
cli_runtime_image="zed-oci-cli-tools:verify"
expected_version="zed $(tr -d '\r\n' < VERSION)"

"$runtime" buildx build \
  --platform "$platform" \
  --file docker/Dockerfile \
  --tag "$image" \
  --load \
  .

version="$($runtime run --rm --platform "$platform" "$image" zed --version)"
case "$version" in
  "$expected_version") ;;
  *) echo "verify: unexpected Zed version: $version" >&2; exit 1 ;;
esac

# These variables intentionally expand in the container.
# shellcheck disable=SC2016
"$runtime" run --rm --platform "$platform" --network none "$image" sh -euc '
  test "$(id -u)" = 10001
  test "$(id -g)" = 10001
  test "$PWD" = /workspace
  test "$HOME" = /home/zed
  test "$ZED_PKG_HOME" = /home/zed/.zed-pkg
  test -w /workspace
  test -w "$ZED_PKG_HOME"
  test -z "$(find "$ZED_PKG_HOME" -mindepth 1 -print -quit)"
  test -z "$(find "$HOME" -mindepth 1 -maxdepth 1 ! -name .zed-pkg -print -quit)"
  test ! -e /root/.zed-pkg
'

"$runtime" build \
  --platform "$platform" \
  --build-arg "ZED_OCI_IMAGE=$image" \
  --file docker/examples/init.Dockerfile \
  --tag "$runtime_image" \
  .

# These variables intentionally expand in the container.
# shellcheck disable=SC2016
"$runtime" run --rm --platform "$platform" --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  "$runtime_image" sh -euc '
  test "$(id -u)" != 0
  ! command -v zed
  test ! -e /home/zed/.zed-pkg
  test -s /app/.zpkg.toml
'

"$runtime" build \
  --platform "$platform" \
  --build-arg "ZED_OCI_IMAGE=$image" \
  --file docker/examples/cli-tools.Dockerfile \
  --tag "$cli_runtime_image" \
  .

# These variables intentionally expand in the container.
# shellcheck disable=SC2016
"$runtime" run --rm --platform "$platform" --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  "$cli_runtime_image" sh -euc '
  test "$(node --version)" = "v24.19.0"
  test "$(nodejs --version)" = "v24.19.0"
  test "$(python3 --version)" = "Python 3.14.7"
  test "$(python --version)" = "Python 3.14.7"
  npm --version
  pip3 --version
  ! command -v zed
  test ! -e /home/zed/.zed-pkg
'

echo "verify: $platform builder and clean Node/Python runtime smoke tests passed"
