# syntax=docker/dockerfile:1

##############################################
# Development: Vite dev server with HMR
##############################################
FROM node:20-alpine AS dev

WORKDIR /app

# Install dependencies first for better layer caching
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Run `npm install` on every start so newly added dependencies in
# package.json are synced into the (anonymous) node_modules volume —
# otherwise the volume created on the first run shadows the image's
# fresh node_modules after adding a package.
CMD ["sh", "-c", "npm install --no-audit --no-fund && npm run dev -- --host 0.0.0.0"]

##############################################
# Build: compile the Vue app into static files
##############################################
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .
RUN npm run build

##############################################
# Production: nginx serving static files + API proxy
##############################################
FROM nginx:1.27-alpine AS prod

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
