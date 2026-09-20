# The Vocalis canvas. Build from the repo root:
#   docker build -f deploy/dashboard.Dockerfile .
FROM node:22-alpine AS build

RUN npm install -g pnpm@12
WORKDIR /app/dashboard

COPY dashboard/package.json dashboard/pnpm-lock.yaml dashboard/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY dashboard/ ./
RUN pnpm build

FROM node:22-alpine AS runtime

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app

# Next's standalone output carries only the server and the files it traced.
COPY --from=build /app/dashboard/.next/standalone ./
COPY --from=build /app/dashboard/.next/static ./.next/static
COPY --from=build /app/dashboard/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
