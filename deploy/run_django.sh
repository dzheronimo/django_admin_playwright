#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Загружаем фикстуры только если данных ещё нет
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from server.apps.applications.models import Application
from django.core.management import call_command

User = get_user_model()

# Если ещё нет ни одного приложения — загружаем initial_applications
if not Application.objects.exists():
    call_command('loaddata', 'initial_applications.json')

# Если ещё нет ни одного суперпользователя — загружаем initial_admin
if not User.objects.filter(is_superuser=True).exists():
    call_command('loaddata', 'initial_admin.json')
EOF

exec gunicorn server.wsgi:application -c /project/gunicorn.conf.py
