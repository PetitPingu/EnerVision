FROM node:22-alpine AS builder

WORKDIR /app

# Contexte de build = racine du repo (voir docker-compose.yml).
COPY apps/dashboard/package.json apps/dashboard/package-lock.json ./
RUN npm ci

COPY apps/dashboard/ .

# Variable publique injectée au build (cf. apps/dashboard/.env.example).
ARG NEXT_PUBLIC_API_BFF_URL=http://localhost:8001
ENV NEXT_PUBLIC_API_BFF_URL=$NEXT_PUBLIC_API_BFF_URL

RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY apps/dashboard/package.json apps/dashboard/package-lock.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./next.config.ts

EXPOSE 3000

CMD ["npm", "start"]
