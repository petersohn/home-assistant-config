#!/bin/bash

set -e
script_dir=$(readlink -e "$(dirname "$0")")
cd "$script_dir"

function setup() {
    python="$1"
    venv_path="$2"
    requirements_path="$3"
    rm -rf "$venv_path"
    "$python" -m virtualenv "$venv_path"
    "${venv_path}/bin/pip" install -r "docker/python_requirements/${requirements_path}"
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
    setup python .venv robot.txt
fi

if [[ -n "$hass" ]]; then
    setup python3.11 AppDaemonIntegrationTest/.hass homeassistant.txt
fi

if [[ -n "$appdaemon" ]]; then
    setup python3.8 AppDaemonIntegrationTest/.appdaemon appdaemon.txt
fi
