# Frontend Dockerfile (Vite build + static serving)
# - Vite requires API base URL at build-time to be embedded.
# - Provide VITE_API_BASE_URL via build ARG.

# ---- Build ----
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (better layer caching)
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build-time env injection for Vite
# Example: docker build --build-arg VITE_API_BASE_URL=https://api.example.com -t ops-pilot-frontend .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---- Serve ----
FROM nginx:1.27-alpine AS runner

# Remove default config and use a simple SPA-friendly one
RUN rm -f /etc/nginx/conf.d/default.conf

# Inline nginx config for SPA routes
RUN printf '%s\n' \
  'server {' \
  '  listen 80;' \
  '  server_name _;' \
  '  root /usr/share/nginx/html;' \
  '  index index.html;' \
  '' \
  '  location / {' \
  '    try_files $uri $uri/ /index.html;' \
  '  }' \
  '}' > /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# No secrets in image; runtime env not needed because Vite inlines VITE_* vars at build time

