#!/bin/bash
set -e

echo "Starting Omnisight AI Detection Service..."
echo "Device: ${DEVICE:-cuda}"
echo "Disabled models: ${DISABLED_MODELS:-none}"

exec python -m src.main
