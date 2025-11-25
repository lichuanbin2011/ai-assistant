/**
 * ============================================================================
 * 输入区域组件 (app/components/chat/InputArea.js)
 * ============================================================================
 *
 * 文件作用：
 *   聊天应用的输入区域，负责用户消息输入和图片上传
 *
 * 主要功能：
 *   1. 文本输入（支持多行、自动调整高度）
 *   2. 图片上传（支持点击上传、拖拽上传、多图上传）
 *   3. 图片预览和删除
 *   4. 发送消息（文本 + 图片）
 *   5. 键盘快捷键（Enter 发送、Shift+Enter 换行）
 *   6. 视觉模型检测（不支持视觉的模型禁用图片上传）
 *   7. 联网搜索开关（保持状态）
 *   8. 停止生成功能
 *   9. 联网搜索状态由父组件管理（防止重置）
 *
 *  【布局修改 v3】：
 *   - 底部提示合并为一行
 *   - 减小输入框高度（从 120px 改为 80px）
 *   - 优化整体布局占比
 *   - 移除图片按钮（保留功能）
 *   - 新增 ChatPDF 按钮
 *
 * ============================================================================
 */

'use client';

// 引入 FileText 图标（文档图标）
import {
  Send,
  Paperclip,
  X,
  Image as ImageIcon,
  Square,
  Globe,
  FileText,
} from 'lucide-react';
import { useRouter } from 'next/navigation'; //  确保导入这个
import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

/**
 * InputArea 组件
 *
 * Props 说明：
 * @param {Function} onSendMessage - 发送消息回调
 * @param {Object} currentModel - 当前选择的 AI 模型
 * @param {boolean} isGenerating - AI 是否正在生成回复
 * @param {Function} onStopGeneration - 停止生成回调
 * @param {boolean} isWebSearchEnabled - 联网搜索是否启用（从父组件接收）
 * @param {Function} onToggleWebSearch - 切换联网搜索状态的回调（调用父组件的函数）
 */
export default function InputArea({
  onSendMessage,
  currentModel,
  isGenerating,
  onStopGeneration,
  isWebSearchEnabled,
  onToggleWebSearch,
}) {
  // ========================================================================
  // 1. 状态管理
  // ========================================================================

  const [input, setInput] = useState('');
  const [images, setImages] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const router = useRouter(); //  确保初始化 router

  // ========================================================================
  // 2. Refs - DOM 引用
  // ========================================================================

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // ========================================================================
  // 3. 发送消息
  // ========================================================================

  const handleSend = () => {
    if (!input.trim() && images.length === 0) return;

    const uploadingImages = images.filter((img) => img.uploading);
    if (uploadingImages.length > 0) {
      alert('请等待图片上传完成');
      return;
    }

    const imageUrls = images.map((img) => img.serverUrl);
    onSendMessage(input.trim(), imageUrls, isWebSearchEnabled);

    setInput('');
    setImages([]);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  // ========================================================================
  // 4. 键盘事件处理
  // ========================================================================

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ========================================================================
  // 5. 文件上传处理
  // ========================================================================

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    processFiles(files);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
  };

  // ========================================================================
  // 6. 图片上传到服务器
  // ========================================================================

  const uploadImageToServer = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        return result.data.url;
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('上传失败:', error);
      alert(`上传失败: ${error.message}`);
      return null;
    }
  };

  const processFiles = async (files) => {
    const imageFiles = files.filter((file) => file.type.startsWith('image/'));

    for (const file of imageFiles) {
      if (file.size > 10 * 1024 * 1024) {
        alert(`文件 ${file.name} 超过 10MB 限制`);
        continue;
      }

      const reader = new FileReader();

      reader.onload = async (e) => {
        const tempImage = {
          file,
          preview: e.target.result,
          name: file.name,
          uploading: true,
        };

        setImages((prev) => [...prev, tempImage]);

        const serverUrl = await uploadImageToServer(file);

        if (serverUrl) {
          setImages((prev) =>
            prev.map((img) =>
              img.file === file ? { ...img, serverUrl, uploading: false } : img
            )
          );
        } else {
          setImages((prev) => prev.filter((img) => img.file !== file));
        }
      };

      reader.readAsDataURL(file);
    }
  };

  // ========================================================================
  // 7. 删除图片
  // ========================================================================

  const handleRemoveImage = (index) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  // ========================================================================
  // 8. 自动调整 Textarea 高度
  // ========================================================================

  const handleInputChange = (e) => {
    setInput(e.target.value);

    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
    }
  };

  // 新增 ChatPDF 按钮点击处理函数（占位）
  const handleChatPDFClick = () => {
    // TODO: 跳转到 ChatPDF 页面
    console.log('点击了 ChatPDF 按钮');
    // 示例：跳转到其他页面
    // window.location.href = '/chatpdf'
    // 或使用 Next.js 路由
    router.push('/chatpdf');
  };

  // ========================================================================
  // 9. 渲染 UI
  // ========================================================================
  return (
    <div className="border-t border-gray-200 bg-white">
      <div className="max-w-4xl mx-auto px-4 py-3">
        {/* ==================================================================
            顶部按钮区（附件 + ChatPDF）
            ================================================================== */}
        <div className="flex items-center gap-3 mb-3">
          {/* 附件按钮 */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={!currentModel.supportsVision}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 
                     hover:bg-gray-100 rounded-lg transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
            title="上传附件"
          >
            <Paperclip className="w-4 h-4" />
            <span>附件</span>
          </button>

          {/* 新增 ChatPDF 按钮 */}
          <button
            onClick={handleChatPDFClick}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 
                     hover:bg-gray-100 rounded-lg transition-colors"
            title="ChatPDF - 与 PDF 对话"
          >
            <FileText className="w-4 h-4" />
            <span>ChatPDF</span>
          </button>
          {/* 新增 ChatPDF 按钮结束 */}

          {/* 图片按钮 - 已隐藏 */}
          {/* 
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={!currentModel.supportsVision}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 
                     hover:bg-gray-100 rounded-lg transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
            title="上传图片"
          >
            <ImageIcon className="w-4 h-4" />
            <span>图片</span>
          </button>
          */}

          {/* 隐藏的文件输入框 */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {/* ==================================================================
            图片预览区域
            ================================================================== */}
        {images.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {images.map((img, index) => (
              <div key={index} className="relative group">
                <img
                  src={img.preview}
                  alt={img.name}
                  className="h-20 w-20 object-cover rounded-lg border border-gray-200"
                />

                <Button
                  variant="destructive"
                  size="icon"
                  className="absolute -top-2 -right-2 h-5 w-5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={() => handleRemoveImage(index)}
                >
                  <X className="h-3 w-3" />
                </Button>

                {/* 上传中提示 */}
                {img.uploading && (
                  <div className="absolute inset-0 bg-black bg-opacity-50 rounded-lg flex items-center justify-center">
                    <div className="text-white text-xs">上传中...</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* ==================================================================
            输入框区域
            ================================================================== */}
        <div
          className={cn('relative', isDragging && 'opacity-50')}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <div
            className={cn(
              'relative flex items-end gap-2 p-2.5 rounded-xl border-2 transition-all duration-300',
              isDragging
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 bg-gray-50 focus-within:bg-white focus-within:border-purple-500 focus-within:ring-2 focus-within:ring-purple-100'
            )}
          >
            {/* ============================================================
                左侧：联网搜索按钮
                ============================================================ */}
            <Button
              variant={isWebSearchEnabled ? 'default' : 'ghost'}
              size="icon"
              className={cn(
                'h-9 w-9 shrink-0 transition-colors',
                isWebSearchEnabled && 'bg-blue-600 hover:bg-blue-700 text-white'
              )}
              onClick={() => {
                onToggleWebSearch(!isWebSearchEnabled);
                console.log('🌐 联网搜索状态:', !isWebSearchEnabled);
              }}
              title={isWebSearchEnabled ? '已启用联网搜索' : '点击启用联网搜索'}
            >
              <Globe className="h-5 w-5" />
            </Button>

            {/* ============================================================
                中间：文本输入框
                ============================================================ */}
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="问我任何问题..."
              className="flex-1 min-h-[80px] max-h-[300px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 p-0 text-base"
              rows={1}
            />

            {/* ============================================================
                右侧：发送/停止按钮
                ============================================================ */}
            {isGenerating ? (
              // 停止按钮
              <Button
                size="icon"
                className="h-9 w-9 shrink-0 rounded-full bg-red-600 hover:bg-red-700 transition-all"
                onClick={onStopGeneration}
                title="停止生成"
              >
                <Square className="h-4 w-4" fill="currentColor" />
              </Button>
            ) : (
              // 发送按钮
              <Button
                size="icon"
                className="h-9 w-9 shrink-0 rounded-full bg-blue-600 hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleSend}
                disabled={!input.trim() && images.length === 0}
                title="发送消息 (Enter)"
              >
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* ==================================================================
            底部提示信息
            ================================================================== */}
        <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
          {/* 联网搜索状态 */}
          <span className="flex items-center gap-1.5">
            🌐
            <span
              className={isWebSearchEnabled ? 'text-green-600 font-medium' : ''}
            >
              {isWebSearchEnabled ? '联网搜索已启用' : '联网搜索未启用'}
            </span>
          </span>

          {/* 图片上传支持 */}
          {currentModel.supportsVision && (
            <span className="flex items-center gap-1.5">📷 支持图片上传</span>
          )}

          {/* 分隔符 */}
          <span className="text-gray-300">|</span>

          {/* 快捷键提示 */}
          <span className="flex items-center gap-1.5 text-gray-400">
            💡 按{' '}
            <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs">
              Enter
            </kbd>{' '}
            发送 ·
            <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs">
              Shift+Enter
            </kbd>{' '}
            换行
          </span>
        </div>
      </div>
    </div>
  );
}
