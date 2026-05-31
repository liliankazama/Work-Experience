#!/usr/bin/env bash
# Installation helper for event_photo_finder
# Run once: bash install.sh

set -euo pipefail

echo "=== Event Photo Finder – Setup ==="

# Check Python version
python3 -c "import sys; assert sys.version_info >= (3,9), 'Python 3.9+ required'" \
  || { echo "Error: Python 3.9 or higher is required."; exit 1; }

# Create virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."

# dlib (required by face_recognition) needs cmake
if ! python3 -c "import dlib" 2>/dev/null; then
  echo ""
  echo "dlib not found – attempting to install via pip (may take a few minutes)."
  echo "If this fails, install CMake first: https://cmake.org/download/"
  echo ""
  pip install --upgrade pip
  pip install dlib
fi

pip install -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Activate the environment: source .venv/bin/activate"
echo ""
echo "Example usage:"
echo "  python main.py \\"
echo "    --url 'https://photographer.pixieset.com/myevent/' \\"
echo "    --reference-dir ~/my_photos/ \\"
echo "    --use-selenium"
echo ""
