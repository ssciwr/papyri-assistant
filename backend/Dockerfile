FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# make directories for the agent to work with; each is a backend route in the
# agent config (WORKSPACE_DIR, MEMORY_DIR, LOGS_DIR)
RUN mkdir -p /app/workspace /app/memory /app/logs

# copy skills to SKILL_DIR's default. COPY puts a directory's contents at the
# destination, so the destination has to name the skills directory itself.
COPY backend/skills /app/skills

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
