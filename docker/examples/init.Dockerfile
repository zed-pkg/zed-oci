# syntax=docker/dockerfile:1.26@sha256:ecfaec9ed6d810b56388c508f4121597bfbba70d41a6dfeee4d8cad5f295fc32

ARG ZED_OCI_IMAGE=zed-oci:local
FROM ${ZED_OCI_IMAGE} AS workspace

RUN zed init project --org example \
    && test -s /workspace/project/.zpkg.toml

FROM debian:bookworm-slim@sha256:e67eeead736ff7bbe258ef088bff683635c561b1fcfefad0806c1df4ab49ce0e

WORKDIR /app
COPY --from=workspace --chown=65532:65532 /workspace/project/ /app/

RUN test -s /app/.zpkg.toml \
    && ! command -v zed \
    && test ! -e /home/zed/.zed-pkg

USER 65532:65532
CMD ["sh", "-euc", "test -s /app/.zpkg.toml; test ! -e /home/zed/.zed-pkg; cat /app/.zpkg.toml"]
