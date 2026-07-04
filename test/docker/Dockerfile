FROM python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Robot framework env (system Python 3.12)
WORKDIR /deps/robot
COPY test/dependencies/robot/ ./
RUN uv sync --no-install-project

# Home Assistant env (Python 3.11, --no-deps)
WORKDIR /deps/homeassistant
COPY test/dependencies/homeassistant/ ./
RUN uv venv /homeassistant --python 3.11 \
    && VIRTUAL_ENV=/homeassistant uv pip install --no-deps -r requirements.txt

# AppDaemon env (Python 3.12)
WORKDIR /deps/appdaemon
COPY test/dependencies/appdaemon/ ./
RUN uv venv /appdaemon --python 3.12 \
    && VIRTUAL_ENV=/appdaemon uv sync --no-install-project
