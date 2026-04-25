FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

EXPOSE 8000 8787

CMD ["python", "-m", "app.server"]
