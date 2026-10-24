# Frontend del Centro de Mando: React compilado y servido por nginx.
FROM node:22-alpine AS build
WORKDIR /web
COPY app/web/package.json app/web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY app/web ./
RUN npm run build

FROM nginx:1.27-alpine
COPY ops/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
