FROM python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /usr/local/bin/

# Robot framework env (Python 3.12 venv)
RUN uv venv /robot --python 3.12
WORKDIR /deps/robot
COPY test/dependencies/robot/ ./
RUN VIRTUAL_ENV=/robot uv sync --frozen --no-install-project --active

# Home Assistant env (Python 3.11, --no-deps)
WORKDIR /deps/homeassistant
COPY test/dependencies/homeassistant/ ./
RUN uv venv /homeassistant --python 3.11 \
    && VIRTUAL_ENV=/homeassistant uv pip install --no-deps -r requirements.txt

# AppDaemon env (Python 3.12 venv)
RUN uv venv /appdaemon --python 3.12
WORKDIR /deps/appdaemon
COPY test/dependencies/appdaemon/ ./
RUN VIRTUAL_ENV=/appdaemon uv sync --frozen --no-install-project --active
