FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# make directories for the agent to work with
RUN mkdir /app/workspace
RUN mkdir /app/memory

# copy skills
COPY backend/skills /app/

# copy and install package
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/src backend/src
COPY backend/configs backend/configs

RUN pip install --no-cache-dir ./backend

EXPOSE 3001

CMD ["papyri-backend"]

FROM runtime AS dev

ENV BACKEND_RELOAD=1
ENV PYTHONPATH=/app/backend/src

CMD ["python", "-m", "papyri_backend"]
