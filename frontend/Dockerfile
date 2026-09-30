FROM node:20-slim AS build
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
ARG BACKEND_URL
ENV BACKEND_URL=${BACKEND_URL}
RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "start"]
