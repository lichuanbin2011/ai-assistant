/**
 * ============================================================================
 * 顶部导航栏组件 (app/components/chat/Header.js)
 * ============================================================================
 *
 * 文件作用：
 *   聊天应用的顶部导航栏，提供全局功能入口
 *
 * 主要功能：
 *   1. 显示应用 Logo 和名称
 *   2. 切换侧边栏显示/隐藏（移动端）
 *   3. AI 模型选择器（下拉菜单）
 *   4. 用户菜单（个人资料、设置、退出登录等）
 *   5. 用户头像显示
 *
 * 组件结构：
 *   Header
 *   ├── 左侧区域
 *   │   ├── 汉堡菜单按钮（移动端）
 *   │   └── Logo + 应用名称
 *   ├── 中间区域
 *   │   └── 模型选择器（下拉菜单）
 *   └── 右侧区域
 *       └── 用户菜单（下拉菜单）
 *
 * 技术特点：
 *   - 响应式设计（移动端显示汉堡菜单）
 *   - NextAuth 集成（退出登录）
 *   - 下拉菜单组件（shadcn/ui）
 *   - 头像组件（支持图片和 Fallback）
 *
 * ============================================================================
 */

'use client';
import {
  Menu,
  ChevronDown,
  User,
  BarChart3,
  Settings,
  LogOut,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { models } from '@/lib/mock-data';
import { signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import log from '@/lib/log';

export default function Header({
  selectedModel,
  onModelChange,
  onToggleSidebar,
  user,
}) {
  const router = useRouter();

  const handleSignOut = async () => {
    try {
      // ==================================================================
      // 步骤 1：调用 NextAuth 的 signOut 方法
      // ==================================================================
      //  signOut 参数：
      //    - redirect: false（不自动跳转，手动控制）
      //    - callbackUrl: '/login'（退出后的回调地址）
      await signOut({
        redirect: false,
        callbackUrl: '/login',
      });

      // ==================================================================
      // 步骤 2：手动跳转到登录页
      // ==================================================================
      //  为什么要手动跳转？
      //    - 可以在跳转前执行其他操作（如清除本地存储）
      //    - 可以自定义跳转逻辑（如根据用户类型跳转到不同页面）
      router.push('/login');
      // ==================================================================
      // 步骤 3：刷新页面（清除客户端缓存）
      // ==================================================================
      //  router.refresh()：
      //    - 刷新当前路由的数据
      //    - 清除 NextAuth 的客户端缓存
      //    - 确保退出登录状态生效
      router.refresh();
    } catch (error) {
      console.error('退出登录失败:', error);
      alert('退出登录失败，请重试');
    }
  };

  // 新增：跳转到个人资料页面
  const handleGoToProfile = () => {
    router.push('/profile');
  };

  return (
    <header className="h-[60px] border-b border-gray-200 flex items-center justify-between px-4 bg-white">
      {/* 左侧：Logo + 汉堡菜单 */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleSidebar}
          className="lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">AI</span>
          </div>
          <span className="font-semibold text-lg text-gray-900">AI Chat</span>
        </div>
      </div>

      {/* 中间：模型选择器 */}
      <div className="flex-1 flex justify-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="min-w-[200px] justify-between">
              <span className="flex items-center gap-2">
                <span>{selectedModel.icon}</span>
                <span>{selectedModel.name}</span>
              </span>
              <ChevronDown className="h-4 w-4 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="center" className="w-[250px]">
            <DropdownMenuLabel>选择模型</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {models.map((model) => (
              <DropdownMenuItem
                key={model.id}
                onClick={() => onModelChange(model)}
                className="cursor-pointer"
              >
                <div className="flex flex-col gap-1 w-full">
                  <div className="flex items-center gap-2">
                    <span>{model.icon}</span>
                    <span className="font-medium">{model.name}</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {model.provider}
                  </span>
                </div>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* 右侧：用户菜单 */}
      <div className="flex items-center gap-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-10 w-10 rounded-full">
              <Avatar className="h-10 w-10">
                <AvatarImage
                  src={user?.avatarUrl || '/avatar-placeholder.png'}
                  alt="用户头像"
                />
                <AvatarFallback className="bg-blue-500 text-white">
                  {user?.name?.charAt(0) || 'U'}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-[200px]">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium">{user?.name || '用户'}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {/* 修改：添加图标和点击事件 */}
            <DropdownMenuItem
              className="cursor-pointer"
              onClick={handleGoToProfile}
            >
              <User className="h-4 w-4 mr-2" />
              个人资料
            </DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer">
              <BarChart3 className="h-4 w-4 mr-2" />
              使用统计
            </DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer">
              <Settings className="h-4 w-4 mr-2" />
              设置
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="cursor-pointer text-red-600 focus:text-red-700"
              onClick={handleSignOut}
            >
              <LogOut className="h-4 w-4 mr-2" />
              退出登录
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
