#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Starting NHA Claims Processor API"
echo "Python: $(python --version)"
echo "Tesseract: $(command -v tesseract || true)"
echo "PORT=${PORT:-8000}"

exec python api.py
