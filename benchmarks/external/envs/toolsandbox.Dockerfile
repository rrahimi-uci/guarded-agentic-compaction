FROM python@sha256:1c06f14f1f45c37c7ba0563077e651f288b728eb4a227db32da92b52794ddb3e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/toolsandbox
COPY . .
RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir . \
    && python -m pip install --no-cache-dir httpx==0.27.2

ENTRYPOINT ["tool_sandbox"]
