# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

ARG ZED_OCI_IMAGE=zed-oci:local
FROM ${ZED_OCI_IMAGE} AS zed-builder

WORKDIR /workspace
RUN zed init project --org example

WORKDIR /workspace/project
RUN zed install --cli nodejs
RUN zed install --cli python3

FROM debian:bookworm-slim@sha256:abd67ffcfa541b485a3dff59865ab629aa048a6c613e639d36e7456b0b229241

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
