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

# node:22-alpine embarque npm/npx/corepack, inutiles à l'exécution (CMD ne
# lance que server.js) et responsables des CVE HIGH/CRITICAL remontées par
# Trivy sur l'image (dépendances internes du CLI npm, sans rapport avec le
# code de l'app).
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
    /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack

# output: "standalone" (next.config.ts) fournit un server.js autonome avec le
# strict minimum de node_modules requis.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
