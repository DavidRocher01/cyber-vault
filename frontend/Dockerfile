FROM node:20.19-alpine3.21 AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# ng build utilise defaultConfiguration=production (angular.json)
# environment.prod.ts contient apiUrl: '/api/v1' — proxié par nginx
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist/cyber-vault-frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
