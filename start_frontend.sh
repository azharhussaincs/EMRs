#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/frontend"

echo "Starting Clinical EMR Frontend Shell on http://localhost:3000..."
exec npm run dev
