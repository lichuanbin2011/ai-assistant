/**
 * ============================================================================
 * 根布局组件 (app/layout.js)
 * ============================================================================
 *
 * 文件作用：
 *   应用的最外层布局，为所有页面提供统一的结构和配置
 *
 * 主要功能：
 *   1. 配置全局字体（Inter）
 *   2. 引入全局样式（Tailwind CSS）
 *   3. 提供 Session 上下文（NextAuth）
 *   4. 设置页面元数据（SEO）
 *
 * 应用范围：
 *   所有页面都会被此布局包裹
 *
 * 技术栈：
 *   - Next.js 17 App Router
 *   - NextAuth.js（身份验证）
 *   - Tailwind CSS（样式）
 *   - Google Fonts（字体）
 *
 * ============================================================================
 */

import { Inter } from 'next/font/google'; // Google 字体加载器
import './globals.css'; // 全局样式（Tailwind CSS）
import { SessionProvider } from 'next-auth/react'; // NextAuth Session 提供者

/**
 * 字体配置
 *
 * Inter：Google 开源的现代无衬线字体
 * subsets: ['latin']：只加载拉丁字符集（减小字体文件大小）
 *
 * 优化：Next.js 会自动优化字体加载（自托管、预加载）
 */
const inter = Inter({ subsets: ['latin'] });

/**
 * 页面元数据
 *
 * 作用：设置 HTML <head> 标签内容，影响 SEO 和浏览器显示
 *
 * title：浏览器标签页标题
 * description：搜索引擎描述
 *
 * 使用：会自动注入到 <head> 标签
 */
export const metadata = {
  title: 'AI Chat - 智能对话助手',
  description: '基于 LangChain 和 OpenRouter 的 AI 聊天应用',
};

/**
 * RootLayout - 根布局组件
 *
 * 作用：
 *   为整个应用提供统一的 HTML 结构和全局配置
 *
 * 参数：
 *   @param {Object} props
 *   @param {React.ReactNode} props.children - 子页面内容
 *
 * 结构层次：
 *   <html>
 *     <body>
 *       <SessionProvider>  ← NextAuth 上下文
 *         {children}       ← 各个页面组件
 *       </SessionProvider>
 *     </body>
 *   </html>
 *
 * 技术细节：
 *   - lang="zh-CN"：设置页面语言为简体中文（影响浏览器行为）
 *   - className={inter.className}：应用 Inter 字体
 *   - SessionProvider：提供全局 Session 状态（用户登录信息）
 *
 * 返回值：
 *   @returns {JSX.Element} 完整的 HTML 结构
 */
export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      {/* 
        body 标签
        - className={inter.className}：应用 Inter 字体到整个页面
      */}
      <body className={inter.className}>
        {/* 
          SessionProvider：NextAuth 的 Session 上下文提供者
          
          作用：
            - 使所有子组件都能访问用户登录状态
            - 提供 useSession() Hook
            - 自动处理 Session 刷新
          
          使用示例：
            const { data: session } = useSession()
        */}
        <SessionProvider>
          {/* 
            children：当前页面的内容
            
            可能的值：
              - app/page.js（主页）
              - app/login/page.js（登录页）
              - app/register/page.js（注册页）
              - 等等...
          */}
          {children}
        </SessionProvider>
      </body>
    </html>
  );
}
