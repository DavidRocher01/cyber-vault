FROM node:20-alpine AS builder

WORKDIR /app

ARG API_URL=http://localhost:8001/api/v1

COPY package*.json ./
RUN npm install

COPY . .

RUN sed -i "s|http://localhost:8000/api/v1|${API_URL}|g" src/environments/environment.ts && \
    npm run build

FROM nginx:alpine
COPY --from=builder /app/dist/cyber-vault-frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
