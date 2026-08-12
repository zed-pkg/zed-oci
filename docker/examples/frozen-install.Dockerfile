# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

# Build from a checked-out application that contains .zpkg.toml and .zpkg.lock:
#   docker build --build-arg ZED_OCI_IMAGE=ghcr.io/zed-pkg/zed-oci:0.2.0@sha256:<digest> \
#     -f docker/examples/frozen-install.Dockerfile .
ARG ZED_OCI_IMAGE=zed-oci:local
FROM ${ZED_OCI_IMAGE} AS dependencies

COPY --chown=10001:10001 .zpkg.toml .zpkg.lock ./
RUN --mount=type=cache,target=/home/zed/.zed-pkg,uid=10001,gid=10001 \
    zed install --frozen --install-mode copy

# Choose a final image that is ABI-compatible with the application and any
# dynamically linked installed tools. Alpine is illustrative, not universal.
FROM alpine:3.22.1@sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1

WORKDIR /app
COPY --from=dependencies --chown=65532:65532 /workspace/ /app/

RUN test ! -e /home/zed/.zed-pkg \
    && ! command -v zed \
    && test -f /app/.zpkg.toml \
    && test -f /app/.zpkg.lock \
    && test -z "$(find /app/zed_modules -type l -print -quit 2>/dev/null)"

USER 65532:65532
