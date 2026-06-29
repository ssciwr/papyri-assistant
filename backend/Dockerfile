FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/src backend/src
RUN pip install --no-cache-dir ./backend

EXPOSE 3001

CMD ["papyri-backend"]

FROM runtime AS dev

ENV BACKEND_RELOAD=1
ENV PYTHONPATH=/app/backend/src

CMD ["python", "-m", "papyri_backend"]
