# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Build with API base baked in; override via compose env if needed
ARG REACT_APP_API_BASE_URL=http://localhost:8000
ENV REACT_APP_API_BASE_URL=$REACT_APP_API_BASE_URL
RUN npm run build

# ---- serve stage ----
FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html
COPY --from=build /app/build/ ./
# Nginx config for SPA (history fallback)
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
LABEL authors="tomeichhorn"