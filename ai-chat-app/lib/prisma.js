// ============================================================================
// Prisma Client 单例模式封装
// ============================================================================
// 文件作用：
//   创建并导出全局唯一的 Prisma Client 实例，避免重复连接数据库
//
// 为什么需要单例模式？
//   1. Next.js 开发环境会热重载（Hot Reload），每次修改代码都会重新导入模块
//   2. 如果每次导入都创建新的 PrismaClient，会导致数据库连接数爆炸
//   3. 使用 globalThis 存储实例，确保整个应用共享同一个连接
// ============================================================================

import { PrismaClient } from '@prisma/client';

// ----------------------------------------------------------------------------
// 创建 Prisma Client 实例
// ----------------------------------------------------------------------------
// 单例模式实现：
//   - 开发环境：使用 globalThis.prisma 缓存实例（避免热重载时重复创建）
//   - 生产环境：直接创建新实例（生产环境不会热重载）
const globalForPrisma = global;

export const prisma = globalForPrisma.prisma || new PrismaClient();
// ----------------------------------------------------------------------------
// 开发环境缓存实例
// ----------------------------------------------------------------------------
// 仅在开发环境下将实例存储到 globalThis，避免热重载时丢失连接
if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
// ============================================================================
// 使用说明
// ============================================================================
//
// 【导入方式】
// import { prisma } from '@/lib/prisma'
//
// 【常见操作示例】
//
// 1. 查询所有用户
// const users = await prisma.user.findMany()
//
// 2. 创建新用户
// const user = await prisma.user.create({
//   data: { email: 'test@example.com', passwordHash: 'xxx' }
// })
//
// 3. 更新用户
// await prisma.user.update({
//   where: { id: 'user_id' },
//   data: { name: 'New Name' }
// })
//
// 4. 删除用户
// await prisma.user.delete({ where: { id: 'user_id' } })
//
// 5. 关联查询（查询用户及其所有会话）
// const user = await prisma.user.findUnique({
//   where: { id: 'user_id' },
//   include: { conversations: true }
// })
//
// ============================================================================
