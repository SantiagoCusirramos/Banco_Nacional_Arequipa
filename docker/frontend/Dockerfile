# Imagen del frontend (Next.js). El contexto de construcción es frontend/.
ARG NODE_IMAGE=node:22-alpine@sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202

FROM ${NODE_IMAGE} AS dependencias
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Con el código y las dependencias de desarrollo: aquí corren lint y pruebas.
FROM dependencias AS pruebas
ENV CI=1 NEXT_TELEMETRY_DISABLED=1
COPY . /fuente
# Un clon usado puede traer node_modules, .next o un .env.local: no entran.
RUN rm -rf /fuente/node_modules /fuente/.next /fuente/.env.local \
    && cp -a /fuente/. /app/ && rm -rf /fuente

# Las direcciones de los servicios se leen al ejecutar (COREDB_URL, CUENTAS_GATEWAY_URL,
# TARJETAS_GATEWAY_URL, SOL_GATEWAY_URL): la imagen no lleva ninguna.
FROM pruebas AS construccion
RUN npm run build && npm prune --omit=dev --no-audit --no-fund

FROM ${NODE_IMAGE}
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=construccion --chown=node:node /app ./
USER node
EXPOSE 3000
CMD ["npm", "start"]
