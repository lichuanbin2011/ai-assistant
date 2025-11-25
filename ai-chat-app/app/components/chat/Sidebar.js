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
import { useState } from 'react';
import {
  Plus,
  Search,
  MessageSquare,
  Edit2,
  Trash2,
  X,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { groupConversationsByTime } from '@/lib/mock-data';
import { cn } from '@/lib/utils';

export default function Sidebar({
  conversations,
  currentConversation,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
  isOpen,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredId, setHoveredId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  // 过滤会话
  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 按时间分组
  const groupedConversations = groupConversationsByTime(filteredConversations);

  // 删除会话
  const handleDelete = (e, convId) => {
    e.stopPropagation();
    onDeleteConversation(convId);
  };

  // 开始重命名
  const handleStartRename = (e, conv) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  // 确认重命名
  const handleConfirmRename = async (e, convId) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      await onRenameConversation(convId, editTitle.trim());
    }
    setEditingId(null);
  };

  // 取消重命名
  const handleCancelRename = (e) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => {}}
        />
      )}

      <aside
        className={cn(
          'w-[280px] bg-[#F9FAFB] border-r border-gray-200 flex flex-col transition-transform duration-300',
          'fixed lg:relative inset-y-0 left-0 z-50',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        <div className="p-4">
          <Button
            onClick={onNewConversation}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Plus className="h-4 w-4 mr-2" />
            新建对话
          </Button>
        </div>

        <ScrollArea className="flex-1 px-2 custom-scrollbar">
          {Object.entries(groupedConversations).map(
            ([group, convs]) =>
              convs.length > 0 && (
                <div key={group} className="mb-4">
                  <div className="px-3 py-2 text-xs font-semibold text-gray-500 flex items-center gap-2">
                    <MessageSquare className="h-3 w-3" />
                    {group}
                  </div>

                  {convs.map((conv) => (
                    <div
                      key={conv.id}
                      onClick={() => onSelectConversation(conv)}
                      onMouseEnter={() => setHoveredId(conv.id)}
                      onMouseLeave={() => setHoveredId(null)}
                      className={cn(
                        'group relative px-3 py-3 mb-1 rounded-lg cursor-pointer transition-all',
                        'hover:bg-white',
                        currentConversation?.id === conv.id
                          ? 'bg-blue-50 border border-blue-200'
                          : 'bg-transparent'
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          {editingId === conv.id ? (
                            <div className="flex items-center gap-1">
                              <Input
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onClick={(e) => e.stopPropagation()}
                                className="h-7 text-sm"
                                autoFocus
                              />
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={(e) => handleConfirmRename(e, conv.id)}
                              >
                                <Check className="h-3 w-3 text-green-600" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={handleCancelRename}
                              >
                                <X className="h-3 w-3 text-red-600" />
                              </Button>
                            </div>
                          ) : (
                            <>
                              <p
                                className={cn(
                                  'text-sm font-medium line-clamp-2',
                                  currentConversation?.id === conv.id
                                    ? 'text-blue-700'
                                    : 'text-gray-700'
                                )}
                              >
                                {conv.title}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">
                                {new Date(conv.updatedAt).toLocaleString(
                                  'zh-CN',
                                  {
                                    month: 'numeric',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit',
                                  }
                                )}
                              </p>
                            </>
                          )}
                        </div>

                        {hoveredId === conv.id && editingId !== conv.id && (
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={(e) => handleStartRename(e, conv)}
                            >
                              <Edit2 className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 text-red-600 hover:text-red-700"
                              onClick={(e) => handleDelete(e, conv.id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )
          )}
        </ScrollArea>

        <div className="p-4 border-t border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              type="text"
              placeholder="搜索对话..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white"
            />
            {searchQuery && (
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6"
                onClick={() => setSearchQuery('')}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
