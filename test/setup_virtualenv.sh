#!/bin/bash

set -e
script_dir=$(readlink -e "$(dirname "$0")")
cd "$script_dir"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install from https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

venv_path=".venv"
if [ ! -d "$venv_path" ]; then
    uv venv --python python3.12 "$venv_path"
fi
(
    cd dependencies/appdaemon
    VIRTUAL_ENV="$script_dir/$venv_path" uv sync --frozen --no-install-project --active
)