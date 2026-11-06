# Local base built by experiments/appworld_reference_study/Dockerfile.
# Before building, verify this tag resolves to the sealed base image ID:
# sha256:bb24405c0bd685433d8d3110a9f99f019af14696a2437e15d718b28dabdb68c7
ARG BASE_IMAGE=gac-appworld-reference:42b5bcf
FROM ${BASE_IMAGE}
# Compatibility amendment before any model calls; benchmark source/data unchanged.
# Preserve the original environment and control failure, not a replacement score.
RUN python -m pip install --no-cache-dir 'sqlalchemy==2.0.44' 'sqlmodel==0.0.44' && python -m pip check
