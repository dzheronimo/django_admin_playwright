#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py loaddata initial_applications.json
python manage.py loaddata initial_admin.json

exec gunicorn server.wsgi:application -c /project/gunicorn.conf.py
