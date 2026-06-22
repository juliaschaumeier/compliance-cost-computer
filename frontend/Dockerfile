# syntax=docker/dockerfile:1
#
# Frontend image for the Compliance-Cost Computer (CCC).
# Build context = ./frontend
#   docker build -f frontend/Dockerfile -t ccc-frontend ./frontend
#
# Relies on Next.js standalone output (`output: "standalone"` in next.config.ts).

# --- Stage 1: build -----------------------------------------------------------
FROM node:20-slim AS builder

WORKDIR /app

# NEXT_PUBLIC_* values are inlined at build time, so they must be set BEFORE
# `npm run build`. Defaults to same-origin "/api" (Caddy strips the prefix).
ARG NEXT_PUBLIC_API_BASE_URL=/api
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# Install dependencies first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the source and build.
COPY . .
RUN npm run build

# --- Stage 2: runtime ---------------------------------------------------------
FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1

# Copy only what the standalone server needs.
# The standalone output already contains a minimal node_modules and server.js.
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Run as the built-in non-root "node" user and give it ownership.
RUN chown -R node:node /app
USER node

EXPOSE 3000

CMD ["node", "server.js"]
