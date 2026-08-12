# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

FROM --platform=$BUILDPLATFORM alpine:3.22.1@sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1 AS zed-release

ARG TARGETARCH
ARG ZED_VERSION=v0.1.0
ARG ZED_AMD64_SHA256=08a05f5994068e4c1ccddc9cfc0dac3562473f04ef7fe8bd6dbd7b3f2dbf599a
ARG ZED_ARM64_SHA256=37d60ac56e46053f7fb6674898607d7e91737b7ca6bf08184906c6240d62210a

RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) target="x86_64-unknown-linux-musl"; checksum="${ZED_AMD64_SHA256}" ;; \
      arm64) target="aarch64-unknown-linux-musl"; checksum="${ZED_ARM64_SHA256}" ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 64 ;; \
    esac; \
    archive="zed-${target}.tar.gz"; \
    url="https://github.com/zed-pkg/zed-cli/releases/download/${ZED_VERSION}/${archive}"; \
    wget -q -O "/tmp/${archive}" "${url}"; \
    printf '%s  %s\n' "${checksum}" "/tmp/${archive}" | sha256sum -c -; \
    mkdir /out; \
    tar -xzf "/tmp/${archive}" -C /out zed; \
    chmod 0755 /out/zed; \
    rm -f "/tmp/${archive}"

FROM alpine:3.22.1@sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1

ARG ZED_VERSION=v0.1.0
ARG SOURCE_URL=https://github.com/zed-pkg/zed-oci
ARG SOURCE_REVISION=local
ARG CREATED=1970-01-01T00:00:00Z

LABEL org.opencontainers.image.title="zed-oci" \
      org.opencontainers.image.description="Auditable OCI builder for the zed-pkg package manager" \
      org.opencontainers.image.url="https://github.com/zed-pkg/zed-oci" \
      org.opencontainers.image.source="${SOURCE_URL}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.version="${ZED_VERSION}" \
      org.opencontainers.image.created="${CREATED}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="docker.io/library/alpine:3.22.1"

USER root

COPY --from=zed-release --chmod=0755 /out/zed /usr/local/bin/zed

RUN set -eux; \
    zed --version; \
    addgroup -S -g 10001 zed; \
    adduser -S -D -H -u 10001 -G zed -h /home/zed -s /bin/sh zed; \
    mkdir -p /home/zed/.zed-pkg /workspace; \
    chown -R 10001:10001 /home/zed /workspace

ENV HOME=/home/zed \
    ZED_PKG_HOME=/home/zed/.zed-pkg

WORKDIR /workspace
USER 10001:10001

CMD ["zed", "--help"]
