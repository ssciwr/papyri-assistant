# papyri-assistant

**This is work in progress.**

## Requirements

- Node.js 20.19 or newer
- Python 3.10 or newer
- Access to an OpenAI compatible LLM inference serverA provider API key, API URL, and chat model for the LangChain chat model

## Run With Docker Compose

```sh

npm run docker:up
```

Set `LLM_API_KEY`, `LLM_API_URL`, and `LLM_MODEL` in the root `.env` before starting compose.
Set `VITE_WARNING_BANNER_TEXT` to show a warning banner above the chat, or leave it empty to hide the banner.

- Frontend: http://localhost:5173
- Backend: http://localhost:3001

This uses `compose.yaml`, which runs Vite and the Python backend with source bind mounts for local development.

## Run Production Compose

```sh
cp .env.example .env
npm run docker:prod
```

Set `LLM_API_KEY`, `LLM_API_URL`, and `LLM_MODEL` in the root `.env` before starting compose. The production setup uses `compose.prod.yaml`, builds the frontend into nginx, proxies browser API calls through `/api`, and only publishes the frontend container.
Set `VITE_WARNING_BANNER_TEXT` before building the frontend image to include the warning banner.

- Frontend: http://localhost by default, or `http://localhost:$FRONTEND_PORT` when `FRONTEND_PORT` is set
- Backend: private compose network service at `backend:3001`
