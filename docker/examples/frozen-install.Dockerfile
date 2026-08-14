# syntax=docker/dockerfile:1.26@sha256:ecfaec9ed6d810b56388c508f4121597bfbba70d41a6dfeee4d8cad5f295fc32

# Build from a checked-out application that contains .zpkg.toml and .zpkg.lock:
#   docker build --build-arg ZED_OCI_IMAGE=ghcr.io/zed-pkg/zed-oci:0.2.2@sha256:<digest> \
#     -f docker/examples/frozen-install.Dockerfile .
ARG ZED_OCI_IMAGE=zed-oci:local
FROM ${ZED_OCI_IMAGE} AS dependencies

COPY --chown=10001:10001 .zpkg.toml .zpkg.lock ./
RUN --mount=type=cache,target=/home/zed/.zed-pkg,uid=10001,gid=10001 \
    zed install --frozen --install-mode copy

# Choose a final image that is ABI-compatible with the application and any
# dynamically linked installed tools. Alpine is illustrative, not universal.
FROM alpine:3.24.1@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b

WORKDIR /app
COPY --from=dependencies --chown=65532:65532 /workspace/ /app/

RUN test ! -e /home/zed/.zed-pkg \
    && ! command -v zed \
    && test -f /app/.zpkg.toml \
    && test -f /app/.zpkg.lock \
    && test -z "$(find /app/zed_modules -type l -print -quit 2>/dev/null)"

USER 65532:65532
