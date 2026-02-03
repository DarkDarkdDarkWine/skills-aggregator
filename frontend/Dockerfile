# 构建阶段
FROM node:18-alpine AS build

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm install

# 复制源代码并构建
COPY . .
RUN npm run build

# 生产镜像
FROM nginx:alpine

RUN rm -rf /docker-entrypoint.d/ 2>/dev/null || true

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-simple.conf /etc/nginx/conf.d/default.conf
COPY start.sh /start.sh

RUN chmod -R 755 /usr/share/nginx/html/ && chmod +x /start.sh

EXPOSE 80

CMD ["/start.sh"]
