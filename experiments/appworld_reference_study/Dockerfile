# Build from the separately pinned, unmodified AppWorld checkout as context.
FROM python@sha256:09a17cad02668ae61ece136b4fd36ac3849e14f670ebedb637ea3e15580525bc
WORKDIR /opt/appworld
COPY pyproject.toml README.pypi.md ./
COPY src ./src
# Bound dependency drift without changing the upstream implementation.
RUN python -m pip install --no-cache-dir 'pydantic==2.12.5' 'fastapi==0.141.1' 'starlette==1.6.0' . && appworld install
ENV APPWORLD_ROOT=/opt/world
RUN appworld download data --root /opt/world && test -d /opt/world/data/tasks
RUN mkdir /work && chmod 1777 /work
WORKDIR /work
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python"]
