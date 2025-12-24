FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Start Vite server with --host to make it accessible from outside the container
CMD ["npm", "run", "dev", "--", "--host"]
