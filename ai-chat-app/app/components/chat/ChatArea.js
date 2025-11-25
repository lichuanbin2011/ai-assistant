/**
 * ============================================================================
 * 聊天区域组件 (app/components/chat/ChatArea.js)
 * ============================================================================
 *
 * 文件作用：
 *   聊天界面的核心容器组件，负责消息显示和输入区域的布局
 *
 * 主要功能：
 *   1. 显示消息列表（用户消息 + AI 回复）
 *   2. 自动滚动到最新消息
 *   3. 空状态提示（无消息时显示欢迎界面）
 *   4. 集成输入区域（发送消息）
 *   5.  【新增】：管理联网搜索状态（接收并传递给 InputArea）
 *
 * 组件结构：
 *   ChatArea
 *   ├── ScrollArea（消息列表容器）
 *   │   ├── 空状态提示（messages.length === 0）
 *   │   └── MessageItem 列表（messages.map）
 *   └── InputArea（输入框）
 *
 * 使用场景：
 *   - 在 ChatLayout 中使用
 *   - 作为主聊天界面的核心组件
 *
 * ============================================================================
 */

'use client';

import { useRef, useEffect } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import MessageItem from './MessageItem';
import InputArea from './InputArea';

/**
 * 聊天区域组件
 *
 * Props 说明：
 *
 * @param {Object} props - 组件属性
 * @param {Array} props.messages - 消息列表
 *   格式：[
 *     {
 *       id: string,              // 消息 ID
 *       role: 'user' | 'assistant',  // 消息角色
 *       content: string,         // 消息内容
 *       images?: string[],       // 图片 URL 数组（可选）
 *       createdAt: Date,         // 创建时间
 *       model?: string           // AI 模型名称（仅 assistant）
 *     }
 *   ]
 *
 * @param {Function} props.onSendMessage - 发送消息回调
 *   参数：(content: string, images?: File[]) => Promise<void>
 *   作用：处理用户发送的消息和图片
 *
 * @param {Function} props.onDeleteMessage - 删除消息回调
 *   参数：(messageId: string) => Promise<void>
 *   作用：删除指定消息
 *
 * @param {Function} props.onRegenerateMessage - 重新生成回调
 *   参数：(messageId: string) => Promise<void>
 *   作用：重新生成 AI 回复（针对 assistant 消息）
 *
 * @param {Function} props.onEditMessage - 编辑消息回调
 *   参数：(messageId: string, newContent: string) => Promise<void>
 *   作用：编辑用户消息内容
 *
 * @param {Function} props.onCopyMessage - 复制消息回调
 *   参数：(content: string) => void
 *   作用：复制消息内容到剪贴板
 *
 * @param {Object} props.currentModel - 当前选择的 AI 模型
 *   格式：{
 *     id: string,           // 模型 ID（如 'gpt-3.5-turbo'）
 *     name: string,         // 模型显示名称
 *     description: string   // 模型描述
 *   }
 *
 * @param {boolean} props.isGenerating - AI 是否正在生成回复
 * @param {Function} props.onStopGeneration - 停止生成回调
 *
 *  【新增】：
 * @param {boolean} props.isWebSearchEnabled - 联网搜索是否启用
 * @param {Function} props.onToggleWebSearch - 切换联网搜索状态的回调
 *
 * 返回值：
 *   React 组件（聊天界面）
 *
 * 使用示例：
 *   <ChatArea
 *     messages={messages}
 *     onSendMessage={handleSendMessage}
 *     onDeleteMessage={handleDeleteMessage}
 *     onRegenerateMessage={handleRegenerate}
 *     onEditMessage={handleEditMessage}
 *     onCopyMessage={handleCopyMessage}
 *     currentModel={currentModel}
 *     isGenerating={isGenerating}
 *     onStopGeneration={handleStopGeneration}
 *     isWebSearchEnabled={isWebSearchEnabled}
 *     onToggleWebSearch={handleToggleWebSearch}
 *   />
 */
export default function ChatArea({
  messages, // 消息列表数组
  onSendMessage, // 发送消息的回调函数
  onDeleteMessage, // 删除消息的回调函数
  onRegenerateMessage, // 重新生成 AI 回复的回调函数
  onEditMessage, // 编辑消息的回调函数
  onCopyMessage, // 复制消息的回调函数
  currentModel, // 当前选择的 AI 模型对象
  isGenerating, // AI 是否正在生成回复
  onStopGeneration, // 停止生成的回调函数
  //  【新增】：接收联网搜索状态和控制函数
  isWebSearchEnabled, // 联网搜索是否启用
  onToggleWebSearch, // 切换联网搜索状态的回调函数
}) {
  // ========================================================================
  // Refs - 用于 DOM 操作和滚动控制
  // ========================================================================

  //  scrollAreaRef：滚动容器的引用
  //    - 用途：可以手动控制滚动位置（如滚动到顶部加载更多）
  //    - 目前未使用，但保留以备后续功能扩展
  const scrollAreaRef = useRef(null);

  //  messagesEndRef：消息列表末尾的占位元素引用
  //    - 用途：自动滚动到最新消息
  //    - 原理：在消息列表末尾放置一个不可见的 div，滚动到它即可
  const messagesEndRef = useRef(null);

  // ========================================================================
  // 副作用：自动滚动到最新消息
  // ========================================================================
  //  为什么需要自动滚动？
  //    - 用户发送消息后，需要看到自己的消息和 AI 回复
  //    - AI 流式输出时，需要跟随内容滚动
  //    - 提升用户体验，避免手动滚动
  useEffect(() => {
    // scrollIntoView：原生 DOM 方法，滚动到指定元素
    // behavior: 'smooth'：平滑滚动动画
    // ?.：可选链操作符，防止 ref 为 null 时报错
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]); // 依赖 messages，每次消息变化时触发
  //  触发时机：
  //    - 用户发送消息
  //    - AI 回复流式更新
  //    - 删除消息
  //    - 编辑消息

  return (
    <div className="flex-1 flex flex-col bg-white">
      {/* ====================================================================
          消息列表区域
          ==================================================================== */}
      <ScrollArea className="flex-1 custom-scrollbar" ref={scrollAreaRef}>
        <div className="max-w-4xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            // ================================================================
            // 空状态：无消息时显示欢迎界面
            // ================================================================
            <div className="flex flex-col items-center justify-center h-full text-center py-20">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mb-4">
                <span className="text-white font-bold text-2xl">AI</span>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                开始新的对话
              </h2>
              <p className="text-gray-500 max-w-md">
                我是您的 AI 助手，可以帮您解答问题、分析图片、编写代码等。
                请在下方输入框中输入您的问题。
              </p>
            </div>
          ) : (
            // ================================================================
            // 消息列表：显示所有历史消息
            // ================================================================
            <div className="space-y-6">
              {messages.map((message, index) => (
                <MessageItem
                  key={message.id}
                  message={message}
                  onDelete={onDeleteMessage}
                  onRegenerate={onRegenerateMessage}
                  onEdit={onEditMessage}
                  onCopy={onCopyMessage}
                  isLast={index === messages.length - 1}
                />
              ))}
              {/* 占位元素：用于自动滚动到底部 */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </ScrollArea>

      {/* ====================================================================
          输入区域（固定在底部）
          ==================================================================== */}
      {/* 
         InputArea 组件：
           - 用户输入消息的地方
           - 支持文本输入、图片上传、模型选择等
        
         onSendMessage：
           - 用户点击发送按钮或按 Enter 键时触发
           - 参数：(content: string, images?: File[])
        
         currentModel：
           - 显示当前选择的 AI 模型
           - 用户可以切换模型
        
         【修改点】：传递联网搜索状态和控制函数
           - isWebSearchEnabled：联网搜索是否启用
           - onToggleWebSearch：切换联网搜索状态的回调函数
      */}

      <InputArea
        onSendMessage={onSendMessage}
        currentModel={currentModel}
        isGenerating={isGenerating}
        onStopGeneration={onStopGeneration}
        isWebSearchEnabled={isWebSearchEnabled}
        onToggleWebSearch={onToggleWebSearch}
      />
    </div>
  );
}
