/**
 * ============================================================================
 * 消息管理 Hook (lib/hooks/useMessages.js)
 * ============================================================================
 *
 * 文件作用：
 *   管理聊天消息的状态和操作（加载、发送、更新、删除）
 *
 * 主要功能：
 *   1. 加载指定会话的消息列表
 *   2. 发送新消息并添加到列表
 *   3. 更新消息内容（支持流式输出）
 *   4. 删除单条消息
 *   5. 新增：导出 setMessages，支持直接操作消息数组
 *
 * 核心技术：
 *   - useState: 管理消息列表、加载状态、错误状态
 *   - useCallback: 缓存函数，避免不必要的重新渲染
 *   - useEffect: 监听 conversationId 变化，自动加载消息
 *
 * 调用位置：
 *   - components/chat/ChatLayout.js（聊天布局组件）
 *
 * 数据流：
 *   用户操作 → Hook 方法 → API 请求 → 更新本地状态 → 组件重新渲染
 *
 * 修改记录：
 *   - 2025-11-15：添加联网搜索支持
 *   - 2025-11-16：导出 setMessages，支持联网搜索实时显示
 *   - 2025-11-21：✨ 修复 userMessage 作用域问题
 * ============================================================================
 */

'use client';
import { useState, useEffect, useCallback } from 'react';
import { conversationsApi, messagesApi } from '@/lib/api-client';
import log from '@/lib/log';

/**
 * ============================================================================
 * useMessages Hook - 消息管理（支持联网搜索和引用来源）
 * ============================================================================
 *
 * 修改记录：
 *   - 2025-11-15：添加联网搜索支持
 *   - 添加 citations 数据处理
 *   - 修复流式输出时 citations 不显示的问题
 *   - 2025-11-16：导出 setMessages，支持联网搜索实时显示
 *   - 2025-11-21：✨ 修复 userMessage 作用域问题
 *
 * 新增功能：
 *   1. 加载消息时包含 citations 字段
 *   2. 流式输出完成后更新 citations
 *   3. 支持 isWebSearch 标记
 *   4. 导出 setMessages，允许外部直接操作消息数组
 *
 * ============================================================================
 */
export function useMessages(conversationId) {
  // --------------------------------------------------------------------------
  // 状态定义
  // --------------------------------------------------------------------------
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // --------------------------------------------------------------------------
  // 核心方法
  // --------------------------------------------------------------------------

  /**
   * loadMessages - 加载消息列表
   *
   * 修改点：
   *   - 确保每条消息都包含 citations 和 isWebSearch 字段
   *   - 添加调试日志
   */
  const loadMessages = useCallback(async () => {
    if (!conversationId) {
      setMessages([]);
      return;
    }

    try {
      setLoading(true);

      // 调用 API 获取消息列表
      const response = await conversationsApi.getMessages(conversationId);

      // 确保每条消息都有 citations 和 isWebSearch 字段
      const messagesWithCitations = response.data.messages.map((msg) => ({
        ...msg,
        citations: msg.citations || [], // 默认空数组
        isWebSearch: msg.isWebSearch || false, // 默认 false
      }));

      // 调试日志（仅开发环境）
      if (process.env.NODE_ENV === 'development') {
        log.debug(
          '📥 useMessages 加载消息:',
          messagesWithCitations.length,
          '条'
        );

        messagesWithCitations.forEach((msg, index) => {
          if (msg.role === 'assistant' && msg.citations?.length > 0) {
            log.debug(`消息 ${index + 1} (${msg.id}):`, {
              role: msg.role,
              isWebSearch: msg.isWebSearch,
              citationsCount: msg.citations.length,
            });
          }
        });
      }

      setMessages(messagesWithCitations);
    } catch (err) {
      setError(err.message);
      console.error('❌ 加载消息失败:', err);
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  /**
   * sendMessage - 发送消息
   *
   * ✨ 修改点：
   *   - 将 userMessage 和 aiMessage 定义提到函数顶部
   *   - 使用可选链访问属性
   *   - 添加 citations 和 isWebSearch 字段到占位消息
   *   - 流式输出完成后刷新消息（确保 citations 同步）
   */
  const sendMessage = useCallback(
    async (content, images, model, skipUserMessage = false) => {
      if (!conversationId) {
        throw new Error('未选择会话');
      }

      // ========================================================================
      // ✅ 修复：在函数顶部定义变量
      // ========================================================================
      let userMessage = null;
      let aiMessage = null;

      try {
        // 调用 API 发送消息
        const response = await conversationsApi.sendMessage(conversationId, {
          content,
          images: images || [],
          model,
        });

        // ======================================================================
        // ✅ 修复：在条件判断内赋值，而不是定义
        // ======================================================================
        if (!skipUserMessage) {
          userMessage = {
            ...response.data.userMessage,
            citations: [],
            isWebSearch: false,
          };
          setMessages((prev) => [...prev, userMessage]);
        }

        // AI 消息始终添加
        aiMessage = {
          ...response.data.aiMessage,
          citations: [],
          isWebSearch: false,
        };

        setMessages((prev) => [...prev, aiMessage]);

        // ======================================================================
        // ✅ 修复：使用可选链访问属性
        // ======================================================================
        if (process.env.NODE_ENV === 'development') {
          log.debug('📤 发送消息:', {
            userMessageId: userMessage?.id, // ✅ 使用可选链
            aiMessageId: aiMessage?.id,     // ✅ 使用可选链
          });
        }

        // 返回 AI 消息 ID（供流式输出使用）
        return response.data.aiMessage.id;
      } catch (err) {
        setError(err.message);
        throw err;
      }
    },
    [conversationId]
  );

  /**
   * updateMessageContent - 更新AI消息内容（流式输出）
   *
   * 修改点：
   *   - 支持同时更新 content、citations 和 isWebSearch
   *   - 添加调试日志
   */
  const updateMessageContent = useCallback(
    (messageId, content, options = {}) => {
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === messageId) {
            // 合并更新：content + citations + isWebSearch
            const updatedMsg = {
              ...msg,
              content,
              ...(options.citations !== undefined && {
                citations: options.citations,
              }),
              ...(options.isWebSearch !== undefined && {
                isWebSearch: options.isWebSearch,
              }),
            };

            // 调试日志（仅在有 citations 时打印）
            if (process.env.NODE_ENV === 'development' && options.citations) {
              log.debug('🔄 更新消息内容:', {
                messageId,
                contentLength: content.length,
                citationsCount: options.citations.length,
                isWebSearch: options.isWebSearch,
              });
            }

            return updatedMsg;
          }
          return msg;
        })
      );
    },
    []
  );

  /**
   * 新增：updateMessageCitations - 单独更新 citations
   *
   * 作用：
   *   流式输出完成后，单独更新消息的 citations 字段
   *
   * 参数：
   *   @param {string} messageId - 消息 ID
   *   @param {Array} citations - 引用来源数组
   *   @param {boolean} isWebSearch - 是否为联网搜索
   */
  const updateMessageCitations = useCallback(
    (messageId, citations, isWebSearch = true) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                citations: citations || [],
                isWebSearch,
              }
            : msg
        )
      );

      // 调试日志
      if (process.env.NODE_ENV === 'development') {
        log.debug('🔗 更新消息 citations:', {
          messageId,
          citationsCount: citations?.length || 0,
          isWebSearch,
        });
      }
    },
    []
  );

  /**
   * 新增：refreshMessage - 刷新单条消息
   *
   * 作用：
   *   从数据库重新加载单条消息（确保 citations 数据完整）
   *
   * 参数：
   *   @param {string} messageId - 消息 ID
   */
  const refreshMessage = useCallback(async (messageId) => {
    try {
      // 调用 API 获取单条消息
      const response = await messagesApi.get(messageId);

      const updatedMessage = {
        ...response.data,
        citations: response.data.citations || [],
        isWebSearch: response.data.isWebSearch || false,
      };

      // 更新本地状态
      setMessages((prev) =>
        prev.map((msg) => (msg.id === messageId ? updatedMessage : msg))
      );

      // 调试日志
      if (process.env.NODE_ENV === 'development') {
        log.debug('🔄 刷新单条消息:', {
          messageId,
          citationsCount: updatedMessage.citations.length,
          isWebSearch: updatedMessage.isWebSearch,
        });
      }
    } catch (err) {
      console.error('❌ 刷新消息失败:', err);
    }
  }, []);

  /**
   * deleteMessage - 删除消息
   *
   * 无需修改
   */
  const deleteMessage = useCallback(async (messageId) => {
    try {
      await messagesApi.delete(messageId);
      setMessages((prev) => prev.filter((msg) => msg.id !== messageId));
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  // --------------------------------------------------------------------------
  // 副作用
  // --------------------------------------------------------------------------

  /**
   * 自动加载消息
   *
   * 无需修改
   */
  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  // --------------------------------------------------------------------------
  // 返回值
  // --------------------------------------------------------------------------

  return {
    messages, // 消息列表（包含 citations 字段）
    setMessages, // 【修改点】：导出 setMessages，允许外部直接操作消息数组
    loading, // 加载状态
    error, // 错误信息
    sendMessage, // 发送消息
    updateMessageContent, // 更新消息内容（支持 citations）
    updateMessageCitations, // 新增：单独更新 citations
    refreshMessage, // 新增：刷新单条消息
    deleteMessage, // 删除消息
    refresh: loadMessages, // 手动刷新所有消息
  };
}
