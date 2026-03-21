# Multi-stage build for CAPP Web Next.js app
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json ./
COPY apps/web/package.json ./apps/web/

# Install dependencies
RUN npm install

# Copy application code
COPY apps/web ./apps/web

# Build Next.js app (install deps in app folder and build)
WORKDIR /app/apps/web
RUN npm install
RUN npm run build

# Production stage - run Next.js server
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./
COPY apps/web/package.json ./apps/web/

# Install production dependencies only (skip lifecycle scripts)
RUN npm install --omit=dev --ignore-scripts

# Copy built app from builder stage
COPY --from=builder /app/apps/web/.next ./apps/web/.next
COPY --from=builder /app/apps/web/public ./apps/web/public

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"

EXPOSE 3000

CMD ["node", "--cwd", "/app/apps/web", "-e", "require('next/dist/bin/next').nextStart([])"]
