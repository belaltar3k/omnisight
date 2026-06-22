# ── Stage 1: Build Angular ────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (layer-cached separately from source)
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

COPY frontend/ .
RUN npm run build

# ── Stage 2: Nginx serving ───────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Drop the default config
RUN rm /etc/nginx/conf.d/default.conf

COPY backend/apps/nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist/public /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
