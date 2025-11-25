/**
 * ============================================================================
 * 个人资料页面组件 (app/profile/page.js)
 * ============================================================================
 *
 * 文件作用：
 *   用户个人资料管理页面，支持编辑用户名、上传头像
 *
 * 主要功能：
 *   1. 显示用户基本信息（用户名、邮箱、角色、注册时间）
 *   2. 编辑用户名
 *   3. 上传和更新头像
 *   4. 显示使用统计（会话数、消息数、使用天数）
 *
 * 路由：/profile
 *
 * 技术栈：
 *   - NextAuth（Session 管理）
 *   - React Hooks（状态管理）
 *   - Shadcn UI（表单组件）
 *
 * ============================================================================
 */

'use client'; // 客户端组件
import { useSession } from 'next-auth/react'; // NextAuth Session Hook
import { useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  User,
  Mail,
  Calendar,
  Shield,
  Camera,
  Save,
  X,
} from 'lucide-react'; // 图标
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

/**
 * ProfilePage - 个人资料页面组件
 *
 * 状态管理：
 *   - isEditing：是否处于编辑模式
 *   - isSaving：是否正在保存
 *   - uploadingAvatar：是否正在上传头像
 *   - formData：表单数据（name, email, avatarUrl）
 */
export default function ProfilePage() {
  const { data: session, update } = useSession(); // 获取 Session 和更新函数
  const router = useRouter();
  const [isEditing, setIsEditing] = useState(false); // 编辑模式
  const [isSaving, setIsSaving] = useState(false); // 保存状态
  const [uploadingAvatar, setUploadingAvatar] = useState(false); // 上传头像状态

  // 表单数据
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    avatarUrl: '',
  });

  /**
   * 初始化表单数据
   * 当 session 加载完成后，填充表单
   */
  useEffect(() => {
    if (session?.user) {
      setFormData({
        name: session.user.name || '',
        email: session.user.email || '',
        avatarUrl: session.user.avatarUrl || '',
      });
    }
  }, [session]);

  /**
   * handleBack - 返回主页
   */
  const handleBack = () => {
    router.push('/');
  };

  /**
   * handleAvatarUpload - 处理头像上传
   *
   * 流程：
   *   1. 验证文件类型和大小
   *   2. 调用上传 API
   *   3. 更新表单数据（需手动保存）
   */
  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 验证文件类型（只允许图片）
    if (!file.type.startsWith('image/')) {
      alert('请上传图片文件');
      return;
    }

    // 验证文件大小（最大 5MB）
    if (file.size > 5 * 1024 * 1024) {
      alert('图片大小不能超过 5MB');
      return;
    }

    setUploadingAvatar(true);

    try {
      // 创建 FormData 对象
      const formData = new FormData();
      formData.append('file', file);

      // 调用上传 API
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        // 更新表单数据（头像 URL）
        setFormData((prev) => ({ ...prev, avatarUrl: result.data.url }));
        alert('头像上传成功！请点击保存按钮更新资料');
      } else {
        alert('头像上传失败：' + result.error);
      }
    } catch (error) {
      console.error('头像上传失败:', error);
      alert('头像上传失败，请重试');
    } finally {
      setUploadingAvatar(false);
    }
  };

  /**
   * handleSave - 保存个人资料
   *
   * 流程：
   *   1. 验证用户名不为空
   *   2. 调用更新 API
   *   3. 更新 NextAuth Session
   *   4. 退出编辑模式
   */
  const handleSave = async () => {
    if (!formData.name.trim()) {
      alert('用户名不能为空');
      return;
    }

    setIsSaving(true);

    try {
      // 调用更新 API
      const response = await fetch('/api/user/profile', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          avatarUrl: formData.avatarUrl,
        }),
      });

      const result = await response.json();

      if (result.success) {
        // 更新 NextAuth Session（重要：同步到全局状态）
        await update({
          ...session,
          user: {
            ...session?.user,
            name: formData.name,
            avatarUrl: formData.avatarUrl,
          },
        });

        alert('个人资料更新成功！');
        setIsEditing(false); // 退出编辑模式
      } else {
        alert('更新失败：' + result.error);
      }
    } catch (error) {
      console.error('更新个人资料失败:', error);
      alert('更新失败，请重试');
    } finally {
      setIsSaving(false);
    }
  };

  /**
   * handleCancel - 取消编辑
   * 恢复表单数据到原始值
   */
  const handleCancel = () => {
    setFormData({
      name: session?.user?.name || '',
      email: session?.user?.email || '',
      avatarUrl: session?.user?.avatarUrl || '',
    });
    setIsEditing(false);
  };

  // 加载中状态
  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ====================================================================
          顶部导航栏
          ==================================================================== */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          {/* 返回按钮 */}
          <Button
            variant="ghost"
            onClick={handleBack}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </Button>
          <h1 className="text-xl font-semibold">个人资料</h1>
          <div className="w-20"></div> {/* 占位元素（保持居中） */}
        </div>
      </div>

      {/* ====================================================================
          主内容区域
          ==================================================================== */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* 基本信息卡片 */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
            <CardDescription>管理你的个人资料和账户设置</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* ----------------------------------------------------------
                头像部分
                ---------------------------------------------------------- */}
            <div className="flex items-center gap-6">
              <div className="relative">
                {/* 头像显示 */}
                <Avatar className="h-24 w-24">
                  <AvatarImage
                    src={formData.avatarUrl || '/avatar-placeholder.png'}
                  />
                  <AvatarFallback className="bg-blue-500 text-white text-2xl">
                    {formData.name?.charAt(0) || 'U'} {/* 首字母 */}
                  </AvatarFallback>
                </Avatar>
                {/* 编辑模式下显示上传按钮 */}
                {isEditing && (
                  <label className="absolute bottom-0 right-0 bg-blue-500 text-white p-2 rounded-full cursor-pointer hover:bg-blue-600 transition-colors">
                    <Camera className="h-4 w-4" />
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden" // 隐藏原生文件输入框
                      onChange={handleAvatarUpload}
                      disabled={uploadingAvatar}
                    />
                  </label>
                )}
              </div>
              {/* 用户信息 */}
              <div>
                <h3 className="text-lg font-semibold">{formData.name}</h3>
                <p className="text-sm text-gray-500">{formData.email}</p>
                {uploadingAvatar && (
                  <p className="text-xs text-blue-500 mt-1">上传中...</p>
                )}
              </div>
            </div>

            <Separator />

            {/* ----------------------------------------------------------
                表单部分
                ---------------------------------------------------------- */}
            <div className="space-y-4">
              {/* 用户名（可编辑） */}
              <div className="space-y-2">
                <Label htmlFor="name" className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  用户名
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, name: e.target.value }))
                  }
                  disabled={!isEditing} // 非编辑模式禁用
                  placeholder="请输入用户名"
                />
              </div>

              {/* 邮箱（不可编辑） */}
              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  邮箱
                </Label>
                <Input
                  id="email"
                  value={formData.email}
                  disabled // 邮箱不可修改
                  className="bg-gray-50"
                />
                <p className="text-xs text-gray-500">邮箱地址不可修改</p>
              </div>

              {/* 角色（只读） */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  账户角色
                </Label>
                <Input
                  value={
                    session?.user?.role === 'admin' ? '管理员' : '普通用户'
                  }
                  disabled
                  className="bg-gray-50"
                />
              </div>

              {/* 注册时间（只读） */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  注册时间
                </Label>
                <Input
                  value={new Date(
                    session?.user?.createdAt || Date.now()
                  ).toLocaleDateString('zh-CN')}
                  disabled
                  className="bg-gray-50"
                />
              </div>
            </div>

            <Separator />

            {/* ----------------------------------------------------------
                操作按钮
                ---------------------------------------------------------- */}
            <div className="flex justify-end gap-3">
              {!isEditing ? (
                // 非编辑模式：显示"编辑资料"按钮
                <Button onClick={() => setIsEditing(true)}>编辑资料</Button>
              ) : (
                // 编辑模式：显示"取消"和"保存"按钮
                <>
                  <Button
                    variant="outline"
                    onClick={handleCancel}
                    disabled={isSaving}
                  >
                    <X className="h-4 w-4 mr-2" />
                    取消
                  </Button>
                  <Button onClick={handleSave} disabled={isSaving}>
                    <Save className="h-4 w-4 mr-2" />
                    {isSaving ? '保存中...' : '保存'}
                  </Button>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* ====================================================================
            使用统计卡片
            ==================================================================== */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>使用统计</CardTitle>
            <CardDescription>你的 AI Chat 使用数据</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 总会话数 */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">总会话数</p>
                <p className="text-2xl font-bold text-blue-600">0</p>
              </div>
              {/* 总消息数 */}
              <div className="bg-green-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">总消息数</p>
                <p className="text-2xl font-bold text-green-600">0</p>
              </div>
              {/* 使用天数 */}
              <div className="bg-purple-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">使用天数</p>
                <p className="text-2xl font-bold text-purple-600">1</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
