/**
 * ============================================================================
 * NextAuth 配置文件 (app/api/auth/[...nextauth]/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   配置 NextAuth.js 认证系统，处理用户登录、Session 管理
 *
 * 主要功能：
 *   1. 配置 Credentials 登录（邮箱 + 密码）
 *   2. 使用 Prisma 适配器连接数据库
 *   3. JWT Session 管理
 *   4. 自定义 Session 数据（添加 id 和 role）
 *
 * 路由：
 *   - POST /api/auth/signin       （登录）
 *   - GET  /api/auth/signout      （登出）
 *   - GET  /api/auth/session      （获取 Session）
 *   - GET  /api/auth/csrf         （CSRF Token）
 *
 * 技术栈：
 *   - NextAuth.js v5（认证库）
 *   - Prisma（数据库适配器）
 *   - bcryptjs（密码验证）
 *
 * ============================================================================
 */

import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials'; // 账号密码登录
import { PrismaAdapter } from '@auth/prisma-adapter'; // Prisma 适配器
import { prisma } from '@/lib/prisma'; // Prisma 客户端
import bcrypt from 'bcryptjs'; // 密码加密库

/**
 * NextAuth 配置
 *
 * 导出对象：
 *   - handlers：HTTP 处理器（GET/POST）
 *   - auth：获取 Session 的函数
 *   - signIn：登录函数
 *   - signOut：登出函数
 */
export const { handlers, auth, signIn, signOut } = NextAuth({
  // ==========================================================================
  // 1. Prisma 适配器（连接数据库）
  // ==========================================================================
  adapter: PrismaAdapter(prisma),
  // 添加这一行：信任所有主机（Docker 环境必需）
  trustHost: true,

  // ==========================================================================
  // 2. 认证提供商配置
  // ==========================================================================
  providers: [
    /**
     * Credentials Provider - 账号密码登录
     *
     * 流程：
     *   1. 用户提交邮箱和密码
     *   2. authorize 函数验证凭据
     *   3. 返回用户对象（成功）或 null（失败）
     */
    Credentials({
      // 登录表单字段定义
      credentials: {
        email: { label: '邮箱', type: 'email' },
        password: { label: '密码', type: 'password' },
      },

      /**
       * authorize - 验证用户凭据
       *
       * @param {Object} credentials - 用户提交的凭据
       * @returns {Object|null} - 用户对象或 null
       */
      async authorize(credentials) {
        // 检查必填字段
        if (!credentials?.email || !credentials?.password) {
          return null; // 返回 null 表示登录失败
        }

        // 查询用户
        const user = await prisma.user.findUnique({
          where: { email: credentials.email },
        });

        // 用户不存在或没有密码哈希
        if (!user || !user.passwordHash) {
          return null;
        }

        // 验证密码
        const isValid = await bcrypt.compare(
          credentials.password, // 用户输入的密码
          user.passwordHash // 数据库中的密码哈希
        );

        if (!isValid) {
          return null; // 密码错误
        }

        // 登录成功，返回用户对象
        return {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role,
        };
      },
    }),
  ],

  // ==========================================================================
  // 3. Session 配置
  // ==========================================================================
  session: {
    strategy: 'jwt', // 使用 JWT 存储 Session（不存储在数据库）
  },

  // ==========================================================================
  // 4. 自定义页面路由
  // ==========================================================================
  pages: {
    signIn: '/login', // 自定义登录页面路径
  },

  // ==========================================================================
  // 5. 回调函数（自定义 Session 和 JWT）
  // ==========================================================================
  callbacks: {
    /**
     * jwt - JWT 回调
     *
     * 作用：在 JWT Token 中添加自定义字段
     * 触发时机：用户登录时、刷新 Token 时
     *
     * @param {Object} token - JWT Token 对象
     * @param {Object} user - 用户对象（仅登录时存在）
     * @returns {Object} - 修改后的 Token
     */
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id; // 添加用户 ID
        token.role = user.role; // 添加用户角色
      }
      return token;
    },

    /**
     * session - Session 回调
     *
     * 作用：将 JWT 中的数据添加到 Session 对象
     * 触发时机：客户端请求 Session 时
     *
     * @param {Object} session - Session 对象
     * @param {Object} token - JWT Token 对象
     * @returns {Object} - 修改后的 Session
     */
    async session({ session, token }) {
      if (token && session.user) {
        session.user.id = token.id; // 添加用户 ID 到 Session
        session.user.role = token.role; // 添加用户角色到 Session
      }
      return session;
    },
  },
});

// ============================================================================
// 6. 导出 HTTP 处理器（Next.js App Router 要求）
// ============================================================================
export const GET = handlers.GET; // 处理 GET 请求（如获取 Session）
export const POST = handlers.POST; // 处理 POST 请求（如登录）
