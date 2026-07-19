FROM node:20-bookworm-slim

WORKDIR /app

COPY package.json package-lock.json turbo.json ./
COPY apps/web/package.json ./apps/web/package.json

RUN npm install && \
    npm install --workspace web --no-save \
      lightningcss-linux-x64-gnu@1.32.0 \
      @tailwindcss/oxide-linux-x64-gnu@4.3.2

COPY apps/web ./apps/web

RUN npm run build --workspace web

EXPOSE 3000

CMD ["npm", "run", "start", "--workspace", "web"]
