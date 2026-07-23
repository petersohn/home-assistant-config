# syntax=docker/dockerfile:1.7
#
# Build with:
#   docker build --build-context deps=. -f test/docker/Dockerfile test/docker/
#
# The repo root is provided as a named "deps" build context so the COPY
# sources can live outside the immediate build context (test/docker/).

FROM python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /usr/local/bin/

# Test env (Python 3.12 venv)
RUN uv venv /test --python 3.12
WORKDIR /deps/test
COPY --from=deps test/dependencies/test/ ./
RUN VIRTUAL_ENV=/test uv sync --frozen --no-install-project --active

# Home Assistant env (Python 3.11, --no-deps)
WORKDIR /deps/homeassistant
COPY --from=deps test/dependencies/homeassistant/ ./
RUN uv venv /homeassistant --python 3.11 \
    && VIRTUAL_ENV=/homeassistant uv pip install --no-deps -r requirements.txt

# AppDaemon env (Python 3.12 venv)
RUN uv venv /appdaemon --python 3.12
WORKDIR /deps/appdaemon
COPY --from=deps test/dependencies/appdaemon/ ./
RUN VIRTUAL_ENV=/appdaemon uv sync --frozen --no-install-project --active
