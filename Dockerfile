FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN pip install --no-cache-dir . && chmod +x /app/docker-entrypoint.sh

# Container binds 0.0.0.0 inside its own network namespace; host exposure is
# controlled by docker-compose (127.0.0.1 only).
EXPOSE 8080
CMD ["/app/docker-entrypoint.sh"]
