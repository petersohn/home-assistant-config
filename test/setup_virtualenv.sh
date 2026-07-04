#!/bin/bash

set -e
script_dir=$(readlink -e "$(dirname "$0")")
cd "$script_dir"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install from https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

function setup_sync() {
    local python="$1"
    local venv_path="$2"
    local deps_dir="$3"
    rm -rf "$venv_path"
    uv venv --python "$python" "$venv_path"
    (
        cd "$deps_dir"
        VIRTUAL_ENV="$script_dir/$venv_path" uv sync --no-install-project --active
    )
}

function setup_hass() {
    local venv_path="AppDaemonIntegrationTest/.hass"
    rm -rf "$venv_path"
    uv venv --python python3.11 "$venv_path"
    VIRTUAL_ENV="$script_dir/$venv_path" \
        uv pip install --no-deps -r "$script_dir/dependencies/homeassistant/requirements.txt"
}

robot=
hass=
appdaemon=

if [[ "$1" == all ]]; then
    robot=1
    hass=1
    appdaemon=1
else
    for env in "$@"; do
        case "$env" in
            robot)
                robot=1
                ;;
            hass)
                hass=1
                ;;
            appdaemon)
                appdaemon=1
                ;;
        esac
    done
fi

if [[ -n "$robot" ]]; then
    setup_sync python3.12 .venv dependencies/robot
fi

if [[ -n "$hass" ]]; then
    setup_hass
fi

if [[ -n "$appdaemon" ]]; then
    setup_sync python3.12 AppDaemonIntegrationTest/.appdaemon dependencies/appdaemon
fi
