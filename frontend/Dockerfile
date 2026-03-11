FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ARG REACT_APP_API_URL=http://localhost:8000
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

RUN NODE_ENV=production npm run build

FROM node:20-alpine

WORKDIR /app

RUN npm install -g sirv-cli

COPY --from=build /app/public ./public

EXPOSE 3000

CMD ["sirv", "public", "--port", "3000", "--single"]
