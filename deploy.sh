docker compose build django
docker build -f deploy/playwright.Dockerfile -t dj_pw_officesud_worker:latest .
docker compose up -d django
