/**
 * ============================================================================
 * 主页面组件 (app/page.js)
 * ============================================================================
 *
 * 文件作用：
 *   应用的根页面，负责身份验证和渲染聊天界面
 *
 * 主要功能：
 *   1. 检查用户登录状态
 *   2. 未登录用户重定向到登录页
 *   3. 已登录用户显示聊天界面
 *
 * 路由：
 *   访问路径：/ (根路径)
 *
 * 技术栈：
 *   - Next.js 14 App Router（服务端组件）
 *   - NextAuth.js（身份验证）
 *
 * ============================================================================
 */

import { auth } from '@/app/api/auth/[...nextauth]/route'; // NextAuth 认证函数
import { redirect } from 'next/navigation'; // Next.js 重定向函数
import ChatLayout from './components/chat/ChatLayout'; // 聊天布局组件
import log from '@/lib/log';

/**
 * Home - 主页面组件（服务端组件）
 *
 * 作用：
 *   应用的入口页面，实现路由守卫功能
 *
 * 流程：
 *   1. 调用 auth() 获取当前登录状态
 *   2. 如果未登录（session 为 null），重定向到 /login
 *   3. 如果已登录，渲染聊天界面
 *
 * 技术细节：
 *   - async function：服务端异步组件
 *   - await auth()：在服务端获取 session（无需客户端请求）
 *   - redirect()：服务端重定向（比客户端重定向更快）
 *
 * 返回值：
 *   @returns {JSX.Element} 聊天界面或重定向
 */
export default async function Home() {
  // 获取当前登录状态
  // session 结构：{ user: { id, email, name }, expires }
  const session = await auth();

  // 未登录时重定向到登录页
  if (!session) {
    redirect('/login');
  }

  // 已登录，渲染聊天界面
  return (
    <main className="h-screen w-full overflow-hidden">
      {/* 
        ChatLayout：聊天主布局
        - 包含侧边栏（会话列表）
        - 包含聊天区域（消息显示和输入）
      */}
      <ChatLayout />
    </main>
  );
}
