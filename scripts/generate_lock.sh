#!/bin/bash
# Generate locked requirements file
# Usage: ./scripts/generate_lock.sh

set -euo pipefail

if ! command -v pip-compile &> /dev/null; then
    echo "Installing pip-tools..."
    pip install pip-tools
fi

pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
