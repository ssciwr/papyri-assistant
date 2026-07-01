FROM node:22-bookworm-slim AS deps

WORKDIR /app

COPY package.json ./
COPY frontend/package.json frontend/package.json
RUN npm install

FROM deps AS dev

COPY frontend ./frontend

EXPOSE 5173

CMD ["npm", "run", "dev", "-w", "frontend", "--", "--host", "0.0.0.0"]

FROM deps AS build

ARG VITE_API_URL=http://localhost:3001
ARG VITE_WARNING_BANNER_TEXT=
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WARNING_BANNER_TEXT=$VITE_WARNING_BANNER_TEXT

COPY frontend ./frontend
RUN npm run build -w frontend

FROM nginx:1.27-alpine AS runtime

RUN mkdir -p /etc/nginx/tls
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80 443
