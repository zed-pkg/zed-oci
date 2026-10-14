# syntax=docker/dockerfile:1.26@sha256:ecfaec9ed6d810b56388c508f4121597bfbba70d41a6dfeee4d8cad5f295fc32

ARG ZED_OCI_IMAGE=zed-oci:local
FROM ${ZED_OCI_IMAGE} AS zed-builder

WORKDIR /workspace
RUN zed init project --org example

WORKDIR /workspace/project
RUN zed install --cli nodejs
RUN zed install --cli python3

FROM debian:bookworm-slim@sha256:7c7b2c966bc9ee8cedfeef67e0e279108992c77681fa595db4a9d65c06ccc587

WORKDIR /app
COPY --from=zed-builder --chown=65532:65532 /workspace/project/ /app/
ENV PATH="/app/.zed/tools/bin:${PATH}"

RUN test "$(node --version)" = "v24.19.0" \
    && test "$(nodejs --version)" = "v24.19.0" \
    && test "$(python3 --version)" = "Python 3.14.7" \
    && test "$(python --version)" = "Python 3.14.7" \
    && npm --version \
    && pip3 --version \
    && ! command -v zed \
    && test ! -e /home/zed/.zed-pkg

USER 65532:65532
CMD ["sh", "-euc", "node --version; python3 --version; test ! -e /home/zed/.zed-pkg"]
