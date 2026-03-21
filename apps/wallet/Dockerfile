# Multi-stage build for CAPP Wallet Next.js app
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json ./
COPY apps/wallet/package.json ./apps/wallet/

# Install dependencies
RUN npm install

# Copy application code
COPY apps/wallet ./apps/wallet

# Build Next.js app (install deps in app folder and build)
WORKDIR /app/apps/wallet
RUN npm install
RUN npm run build

# Production stage - run Next.js server
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./
COPY apps/wallet/package.json ./apps/wallet/

# Install production dependencies only (skip lifecycle scripts)
RUN npm install --omit=dev --ignore-scripts

# Copy built app from builder stage
COPY --from=builder /app/apps/wallet/.next ./apps/wallet/.next
COPY --from=builder /app/apps/wallet/public ./apps/wallet/public

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"

EXPOSE 3000

CMD ["node", "--cwd", "/app/apps/wallet", "-e", "require('next/dist/bin/next').nextStart([])"]
