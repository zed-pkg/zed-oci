# syntax=docker/dockerfile:1.26@sha256:ecfaec9ed6d810b56388c508f4121597bfbba70d41a6dfeee4d8cad5f295fc32

FROM --platform=$BUILDPLATFORM alpine:3.24.1@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b AS zed-release

ARG TARGETARCH
ARG ZED_VERSION=v0.2.2
ARG ZED_AMD64_SHA256=e977d3484ee91f6cac0a867dcda9cb9fd67a3a37955a9531cc3e0af993f34308
ARG ZED_ARM64_SHA256=94fa9aeed6c83716b871e8a7f02bcb0b11a18653972653914f6d292187f9a2b4

RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) target="x86_64-unknown-linux-musl"; checksum="${ZED_AMD64_SHA256}" ;; \
      arm64) target="aarch64-unknown-linux-musl"; checksum="${ZED_ARM64_SHA256}" ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 64 ;; \
    esac; \
    archive="zed-${target}.tar.gz"; \
    url="https://github.com/zed-pkg/zed-cli/releases/download/${ZED_VERSION}/${archive}"; \
    attempt=1; \
    while ! wget -q -O "/tmp/${archive}" "${url}"; do \
      rm -f "/tmp/${archive}"; \
      if [ "${attempt}" -ge 5 ]; then \
        echo "failed to download ${archive} after ${attempt} attempts" >&2; \
        exit 1; \
      fi; \
      sleep "$((attempt * 2))"; \
      attempt="$((attempt + 1))"; \
    done; \
    printf '%s  %s\n' "${checksum}" "/tmp/${archive}" | sha256sum -c -; \
    test "$(tar -tzf "/tmp/${archive}")" = "zed"; \
    tar -tvzf "/tmp/${archive}" | awk \
      'NR == 1 && substr($1, 1, 1) == "-" { regular = 1 } END { exit !(NR == 1 && regular) }'; \
    mkdir /out; \
    tar -xzf "/tmp/${archive}" -C /out zed; \
    chmod 0755 /out/zed; \
    rm -f "/tmp/${archive}"

FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171

ARG ZED_VERSION=v0.2.2
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
      org.opencontainers.image.base.name="docker.io/library/debian:bookworm-slim" \
      org.opencontainers.image.base.digest="sha256:abd67ffcfa541b485a3dff59865ab629aa048a6c613e639d36e7456b0b229241"

USER root

COPY --from=zed-release --chmod=0755 /out/zed /usr/local/bin/zed

RUN --network=none set -eux; \
    zed --version; \
    groupadd --gid 10001 zed; \
    useradd --uid 10001 --gid 10001 --home-dir /home/zed --no-create-home --shell /bin/sh zed; \
    mkdir -p /home/zed/.zed-pkg /workspace; \
    chown -R 10001:10001 /home/zed /workspace

ENV HOME=/home/zed \
    ZED_PKG_HOME=/home/zed/.zed-pkg

WORKDIR /workspace
USER 10001:10001

CMD ["zed", "--help"]
