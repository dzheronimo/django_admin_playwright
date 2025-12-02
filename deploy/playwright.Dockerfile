FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libxkbcommon0 \
    libdrm2 \
    libxshmfence1 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY ./src/requirements/app.txt requirements.txt

ENV PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1

RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

# Кладём код проекта
COPY . .

# Воркдир — туда, где лежит application/
WORKDIR /app/src

# Вход: будем ждать, что нам передадут EXCEL_PATH через аргументы контейнера
ENTRYPOINT ["python", "-m", "application.officesud.server_worker"]