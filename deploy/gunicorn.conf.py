import os

bind = "0.0.0.0:8005"
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
reload = False