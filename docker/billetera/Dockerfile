# Imagen de la API de Chaski (Billetera Digital). El contexto es billetera-chaski/backend/.
# Solo Express en producción; las pruebas (node:test, sin dependencias) van en la imagen y
# corren con: docker run --rm bna/billetera:local npm test
ARG NODE_IMAGE=node:22-alpine@sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202
FROM ${NODE_IMAGE}
ENV NODE_ENV=production NPM_CONFIG_UPDATE_NOTIFIER=false
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
COPY server.js coredb.js ./
COPY test ./test
USER node
EXPOSE 3000
CMD ["node", "server.js"]
