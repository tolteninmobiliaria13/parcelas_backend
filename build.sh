#!/usr/bin/env bash
# Script de build para Render
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
