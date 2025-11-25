# ============================================================================
# 多阶段构建 Dockerfile
# ============================================================================

# 阶段 1: 依赖安装
FROM node:24-alpine AS deps
WORKDIR /app

# 复制依赖文件
COPY package.json package-lock.json ./
COPY prisma ./prisma/

# 修改：安装所有依赖（包括开发依赖，确保 tiktoken 等包完整安装）
# 安装依赖并全局安装 Prisma
# RUN npm ci && \
#     npm install -g prisma@6.19.0 && \
#     prisma generate
# ✅ 添加：配置 npm 使用淘宝镜像源
RUN npm config set registry https://registry.npmmirror.com && \
    npm ci && \
    npm install -g prisma@6.19.0 && \
    prisma generate

# 阶段 2: 构建应用
FROM node:24-alpine AS builder
WORKDIR /app

# 复制依赖
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 生成 Prisma Client
RUN npm exec prisma generate
# RUN npx prisma generate

# 构建 Next.js 应用
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# 阶段 3: 运行时
FROM node:24-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# 创建非 root 用户
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# ============================================================================
# ✅ 添加：在 runner 阶段安装 Prisma CLI
# ============================================================================
RUN npm config set registry https://registry.npmmirror.com && \
    npm install -g prisma@6.19.0

# ============================================================================
# ✅ 修复 1：创建上传目录（只设置 /app/public 的权限）
# ============================================================================
RUN mkdir -p /app/public/uploads/images /app/public/uploads/pdfs && \
    chown -R nextjs:nodejs /app/public

# ============================================================================
# ✅ 修复 2：复制文件时添加 --chown 参数
# ============================================================================
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma

# 复制 tiktoken 相关依赖
COPY --from=builder /app/node_modules/tiktoken ./node_modules/tiktoken

# 复制 langchain 相关依赖
COPY --from=builder /app/node_modules/@langchain ./node_modules/@langchain
COPY --from=builder /app/node_modules/langchain ./node_modules/langchain

# ============================================================================
# ✅ 修复 3：删除错误的 RUN 命令（删除第 66-69 行）
# ============================================================================
# RUN if [ -d "/tmp/builder/node_modules/@dqbd" ]; then \
#         mkdir -p ./node_modules/@dqbd && \
#         cp -r /tmp/builder/node_modules/@dqbd/* ./node_modules/@dqbd/ || true; \
#     fi

# 设置 WASM 文件权限
RUN find ./node_modules -name "*.wasm" -exec chmod 644 {} \; 2>/dev/null || true

# ============================================================================
# ✅ 修复 4：在复制完所有文件后，统一设置权限
# ============================================================================
RUN chown -R nextjs:nodejs /app

# 设置 node_modules 权限
RUN chown -R nextjs:nodejs /app/node_modules 2>/dev/null || true

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# 设置 tiktoken 相关环境变量
ENV TIKTOKEN_CACHE_DIR=/tmp/tiktoken_cache

CMD ["node", "server.js"]
