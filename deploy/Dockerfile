FROM python:3.13-slim-bookworm

ENV PROJECT_ROOT=/project
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR $PROJECT_ROOT

# requirements
COPY ./src/requirements/site.txt ./requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# app sources
COPY ./src/ $PROJECT_ROOT/

# entrypoint + gunicorn config
COPY ./deploy/run_django.sh /project/run_django.sh
COPY ./deploy/gunicorn.conf.py /project/gunicorn.conf.py
RUN sed -i 's/\r$//' /project/run_django.sh && chmod +x /project/run_django.sh

EXPOSE 8000
CMD ["/project/run_django.sh"]
