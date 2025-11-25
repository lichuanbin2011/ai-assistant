/**
 * ============================================================================
 * 会话管理 Hook (lib/hooks/useConversations.js)
 * ============================================================================
 *
 * 文件作用：
 *   管理聊天会话的状态和操作（加载、创建、更新、删除、生成标题）
 *
 * 主要功能：
 *   1. 加载用户的所有会话列表
 *   2. 创建新会话并自动选中
 *   3. 更新会话信息（如标题）
 *   4. 删除会话并自动切换
 *   5. AI 自动生成会话标题
 *
 * 核心技术：
 *   - useState: 管理会话列表、当前会话、加载状态、错误状态
 *   - useCallback: 缓存操作函数，避免不必要的重新渲染
 *   - useEffect: 监听 userId 变化，自动加载会话列表
 *
 * 调用位置：
 *   - app/page.js（主页面，传递给 Sidebar 和 ChatArea）
 *
 * 数据流：
 *   用户操作 → Hook 方法 → API 请求 → 更新本地状态 → 组件重新渲染
 * ============================================================================
 */

'use client';
import { useState, useEffect, useCallback } from 'react';
import { conversationsApi } from '@/lib/api-client';

/**
 * ----------------------------------------------------------------------------
 * useConversations Hook - 会话管理
 * ----------------------------------------------------------------------------
 *
 * 作用：
 *   封装会话相关的所有状态和操作，提供统一的接口给组件使用
 *
 * 参数：
 *   @param {string} userId - 用户 ID
 *
 * 返回值：
 *   @returns {Object} {
 *     conversations: Array,           // 会话列表
 *     currentConversation: Object,    // 当前选中的会话
 *     setCurrentConversation: Function, // 切换会话
 *     loading: boolean,               // 加载状态
 *     error: string|null,             // 错误信息
 *     createConversation: Function,   // 创建会话
 *     updateConversation: Function,   // 更新会话
 *     deleteConversation: Function,   // 删除会话
 *     generateTitle: Function,        // 生成标题
 *     refresh: Function               // 手动刷新
 *   }
 *
 * 使用示例：
 *   const { conversations, createConversation } = useConversations(userId)
 *   await createConversation('新对话', 'gpt-4o')
 */
export function useConversations(userId) {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 加载会话列表
  const loadConversations = useCallback(async () => {
    if (!userId) return;

    try {
      setLoading(true);
      const response = await conversationsApi.list({ userId });
      setConversations(response.data.conversations);

      // 如果有会话，默认选中第一个
      if (response.data.conversations.length > 0 && !currentConversation) {
        setCurrentConversation(response.data.conversations[0]);
      }
    } catch (err) {
      setError(err.message);
      console.error('加载会话失败:', err);
    } finally {
      setLoading(false);
    }
  }, [userId, currentConversation]);

  // 创建新会话

  /**
   * createConversation - 创建新会话
   *
   * 作用：
   *   创建一个新的聊天会话并自动选中
   *
   * 参数：
   *   @param {string} title - 会话标题（可选，默认 '新对话'）
   *   @param {string} model - AI 模型（可选，默认 'gpt-4o'）
   *
   * 返回值：
   *   @returns {Promise<Object>} 新创建的会话对象
   *
   * 流程：
   *   1. 调用 API 创建会话
   *   2. 将新会话添加到列表开头
   *   3. 自动选中新会话
   *   4. 返回新会话对象
   *
   * 技术细节：
   *   - 使用扩展运算符 [...prev] 保持不可变更新
   *   - 新会话放在开头，符合用户习惯（最新的在上面）
   *
   * 调用位置：
   *   - components/chat/Sidebar.js 的 "新建对话" 按钮
   */
  const createConversation = useCallback(
    async (title, model) => {
      try {
        const response = await conversationsApi.create({
          userId,
          title: title || '新对话',
          model: model || 'gpt-4o',
        });

        const newConv = response.data;
        setConversations((prev) => [newConv, ...prev]);
        setCurrentConversation(newConv);
        return newConv;
      } catch (err) {
        setError(err.message);
        throw err;
      }
    },
    [userId]
  );

  // 更新会话
  const updateConversation = useCallback(
    async (id, data) => {
      try {
        const response = await conversationsApi.update(id, data);
        setConversations((prev) =>
          prev.map((conv) => (conv.id === id ? response.data : conv))
        );
        if (currentConversation?.id === id) {
          setCurrentConversation(response.data);
        }
      } catch (err) {
        setError(err.message);
        throw err;
      }
    },
    [currentConversation]
  );

  // 删除会话
  const deleteConversation = useCallback(
    async (id) => {
      try {
        await conversationsApi.delete(id);
        setConversations((prev) => prev.filter((conv) => conv.id !== id));

        // 如果删除的是当前会话，切换到第一个
        if (currentConversation?.id === id) {
          const remaining = conversations.filter((conv) => conv.id !== id);
          setCurrentConversation(remaining[0] || null);
        }
      } catch (err) {
        setError(err.message);
        throw err;
      }
    },
    [conversations, currentConversation]
  );

  // 生成标题
  const generateTitle = useCallback(
    async (id) => {
      try {
        const response = await conversationsApi.generateTitle(id);
        await updateConversation(id, { title: response.data.title });
      } catch (err) {
        console.error('生成标题失败:', err);
      }
    },
    [updateConversation]
  );

  // 初始加载
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return {
    conversations,
    currentConversation,
    setCurrentConversation,
    loading,
    error,
    createConversation,
    updateConversation,
    deleteConversation,
    generateTitle,
    refresh: loadConversations,
  };
}
