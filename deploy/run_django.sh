#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn server.wsgi:application -c /project/gunicorn.conf.py
