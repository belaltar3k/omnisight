FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --cache /root/.npm

COPY . .

ARG SERVICE_NAME
RUN npx nest build ${SERVICE_NAME}

# ---- runtime ----
FROM node:20-alpine
WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json ./

ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}

CMD node dist/apps/${SERVICE_NAME}/main
