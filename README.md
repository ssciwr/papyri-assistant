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

The stack also starts a pgvector-enabled PostgreSQL database for Scrapyrus. The
Scrapyrus management image is available as a one-off tool container and is not
started by the regular `up` command. Run ingestion commands with:

```sh
docker compose run --build --rm scrapyrus scrapyrus metadata ingest
docker compose run --build --rm scrapyrus scrapyrus transcriptions ingest
```

The management image installs Scrapyrus from PyPI and does not depend on a
local Scrapyrus checkout. Mount ingestion data into a one-off container when
needed, for example:

```sh
docker compose run --build --rm \
  -v /path/to/idp.data:/data/idp.data:ro \
  scrapyrus scrapyrus --idp-data /data/idp.data metadata ingest
```

Embedding ingestion can reach a service running on the Docker host through
`host.docker.internal`.

## Run Production Compose

```sh
cp .env.example .env
npm run docker:prod
```

Set `LLM_API_KEY`, `LLM_API_URL`, and `LLM_MODEL` in the root `.env` before starting compose. The production setup uses `compose.prod.yaml`, builds the frontend into nginx, proxies browser API calls through `/api`, and only publishes the frontend container.
Set `VITE_WARNING_BANNER_TEXT` before building the frontend image to include the warning banner.
Production builds the frontend with `PROD_VITE_API_URL=/api` by default so browser API calls stay on the HTTPS origin and go through nginx.
Put the TLS certificate chain and private key somewhere outside git, then set `TLS_CERTIFICATE_PATH` and `TLS_PRIVATE_KEY_PATH` in `.env`. By default, production compose expects `./certs/tls.pem` and `./certs/tls.key`.

If your provider gave you a `.p7b` bundle for the chain, nginx still needs PEM files. Convert the bundle with `openssl pkcs7 -print_certs -in your-bundle.p7b -out chain.pem` and add `-inform DER` if your bundle is DER encoded. Then concatenate your server certificate PEM first and `chain.pem` after it into the file referenced by `TLS_CERTIFICATE_PATH`.

- Frontend: https://localhost by default, or `https://localhost:$FRONTEND_HTTPS_PORT` when `FRONTEND_HTTPS_PORT` is set
- HTTP port 80 redirects to HTTPS by default, or use `FRONTEND_HTTP_PORT` and `FRONTEND_HTTPS_PORT` to change the published ports
- Backend: private compose network service at `backend:3001`

The production Compose setup has the same PostgreSQL and Scrapyrus management
services. Prefix the ingestion command with the production Compose file:

```sh
docker compose -f compose.prod.yaml run --build --rm scrapyrus scrapyrus metadata ingest
```
