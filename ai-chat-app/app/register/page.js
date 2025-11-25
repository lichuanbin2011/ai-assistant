/**
 * ============================================================================
 * 注册页面组件 (app/register/page.js)
 * ============================================================================
 *
 * 文件作用：
 *   用户注册页面，收集用户信息并创建账户
 *
 * 主要功能：
 *   1. 表单验证（密码一致性、长度检查）
 *   2. 调用注册 API
 *   3. 注册成功后跳转到登录页
 *
 * 路由：/register
 *
 * 技术栈：
 *   - React Hooks（状态管理）
 *   - Next.js 客户端组件
 *   - Shadcn UI（表单组件）
 *
 * ============================================================================
 */

'use client'; // 客户端组件（使用 React Hooks）
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

/**
 * RegisterPage - 注册页面组件
 *
 * 状态管理：
 *   - email：邮箱
 *   - password：密码
 *   - confirmPassword：确认密码
 *   - name：用户名（可选）
 *   - error：错误信息
 *   - loading：加载状态
 */
export default function RegisterPage() {
  const [email, setEmail] = useState(''); // 邮箱
  const [password, setPassword] = useState(''); // 密码
  const [confirmPassword, setConfirmPassword] = useState(''); // 确认密码
  const [name, setName] = useState(''); // 用户名（可选）
  const [error, setError] = useState(''); // 错误提示
  const [loading, setLoading] = useState(false); // 加载状态
  const router = useRouter(); // 路由对象（用于跳转）

  /**
   * handleSubmit - 处理表单提交
   *
   * 流程：
   *   1. 验证密码一致性
   *   2. 验证密码长度
   *   3. 调用注册 API
   *   4. 成功后跳转到登录页
   */
  const handleSubmit = async (e) => {
    e.preventDefault(); // 阻止表单默认提交
    setError(''); // 清空错误信息

    // 验证密码一致性
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    // 验证密码长度
    if (password.length < 6) {
      setError('密码长度至少6位');
      return;
    }

    setLoading(true); // 开始加载

    try {
      // 调用注册API
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, name }), // 发送用户数据
      });

      const data = await response.json(); // 解析响应

      // 检查响应状态
      if (!response.ok) {
        throw new Error(data.error || '注册失败');
      }

      // 注册成功，跳转到登录页
      alert('注册成功！请登录');
      router.push('/login');
    } catch (err) {
      setError(err.message); // 显示错误信息
    } finally {
      setLoading(false); // 结束加载
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      {/* 注册卡片 */}
      <Card className="w-full max-w-md">
        {/* 卡片头部 */}
        <CardHeader className="space-y-1">
          {/* Logo */}
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center">
              <span className="text-white font-bold text-2xl">AI</span>
            </div>
          </div>
          <CardTitle className="text-2xl text-center">注册 AI Chat</CardTitle>
          <CardDescription className="text-center">
            创建您的账户以开始使用
          </CardDescription>
        </CardHeader>

        {/* 卡片内容 */}
        <CardContent>
          {/* 注册表单 */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 用户名输入框（可选） */}
            <div className="space-y-2">
              <label className="text-sm font-medium">用户名（可选）</label>
              <Input
                type="text"
                placeholder="张三"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            {/* 邮箱输入框（必填） */}
            <div className="space-y-2">
              <label className="text-sm font-medium">邮箱</label>
              <Input
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            {/* 密码输入框（必填） */}
            <div className="space-y-2">
              <label className="text-sm font-medium">密码</label>
              <Input
                type="password"
                placeholder="至少6位"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {/* 确认密码输入框（必填） */}
            <div className="space-y-2">
              <label className="text-sm font-medium">确认密码</label>
              <Input
                type="password"
                placeholder="再次输入密码"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">
                {error}
              </div>
            )}

            {/* 提交按钮 */}
            <Button
              type="submit"
              className="w-full"
              disabled={loading} // 加载时禁用
            >
              {loading ? '注册中...' : '注册'}
            </Button>
          </form>

          {/* 跳转到登录页链接 */}
          <div className="mt-4 text-center text-sm text-gray-600">
            已有账户？{' '}
            <a href="/login" className="text-blue-600 hover:underline">
              登录
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
