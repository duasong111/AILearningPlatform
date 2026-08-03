FROM node:22-alpine

WORKDIR /app

# 利用 Docker 层缓存: 先只拷 package 文件装依赖
COPY package.json package-lock.json ./
RUN npm ci

# 源码通过 volume 挂载, 这里只 COPY 保证镜像可独立构建
COPY . .

EXPOSE 35173

# vite dev server, --host 让容器外可访问
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "35173"]
