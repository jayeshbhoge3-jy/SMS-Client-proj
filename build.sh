#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Compile translation messages if any exist
python manage.py compilemessages || true

# Collect static files into STATIC_ROOT using WhiteNoise
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate
