/**
 * ============================================================================
 * ChatPDF 页面组件 (app/chatpdf/page.js) - 添加 Markdown 和复制功能
 * ============================================================================
 *
 * 文件作用：
 *   提供 PDF 文件上传和智能对话功能
 *
 * 主要功能：
 *   1. PDF 文件上传
 *   2. PDF 文件列表管理（侧边栏）
 *   3. 与 PDF 内容进行 AI 对话
 *   4. 模型选择（GPT-4o、Claude 等）
 *   5. 新增：Markdown 渲染支持
 *   6. 新增：复制功能
 *
 * 技术栈：
 *   - Next.js 16 App Router
 *   - NextAuth.js（身份验证）
 *   - Tailwind CSS（样式）
 *   - 新增：React Markdown（Markdown 渲染）
 * ============================================================================
 */
'use client';

import { useState, useRef, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import {
  Upload,
  FileText,
  Send,
  Loader2,
  X,
  ChevronDown,
  Link as LinkIcon,
  ArrowLeft,
  RefreshCw,
  //新增复制相关图标
  Copy,
  Check,
} from 'lucide-react';
// 导入 pdfApi
import { pdfApi } from '@/lib/api-client';

// 新增 Markdown 相关导入
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import log from '@/lib/log';

export default function ChatPDF() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // ========================================================================
  // 状态管理
  // ========================================================================
  // PDF 文件相关
  const [pdfFiles, setPdfFiles] = useState([]); // PDF 文件列表
  const [currentPdf, setCurrentPdf] = useState(null); // 当前选中的 PDF
  const [isUploading, setIsUploading] = useState(false); // 上传中
  const [isDragging, setIsDragging] = useState(false); // 拖拽状态
  const [isLoadingList, setIsLoadingList] = useState(false); // 列表加载状态

  // 新增状态
  const [pdfStatus, setPdfStatus] = useState({}); // PDF 处理状态映射

  // 添加错误和成功提示状态
  const [uploadError, setUploadError] = useState(''); // 上传错误信息
  const [uploadSuccess, setUploadSuccess] = useState(''); // 上传成功信息

  // 聊天相关
  const [messages, setMessages] = useState([]); // 聊天消息
  const [inputMessage, setInputMessage] = useState(''); // 输入框内容
  const [isGenerating, setIsGenerating] = useState(false); // AI 生成中

  // 新增复制功能状态
  const [copiedMessageId, setCopiedMessageId] = useState(null); // 复制功能状态

  // 模型选择
  const [selectedModel, setSelectedModel] = useState('openai/gpt-4o');
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  // URL 上传
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [urlInput, setUrlInput] = useState('');

  // Refs
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const dropZoneRef = useRef(null);
  const modelDropdownRef = useRef(null);

  // ========================================================================
  // 模型列表
  // ========================================================================
  const models = [
    {
      id: 'openai/gpt-4o',
      name: 'GPT-4o',
      icon: '🚀',
      description: '最强大的模型',
    },
    {
      id: 'openai/gpt-4o-mini',
      name: 'GPT-4o Mini',
      icon: '⚡',
      description: '快速且经济',
    },
    {
      id: 'anthropic/claude-3.5-sonnet',
      name: 'Claude 3.5 Sonnet',
      icon: '🧠',
      description: '擅长分析',
    },
    {
      id: 'google/gemini-pro-1.5',
      name: 'Gemini Pro 1.5',
      icon: '💎',
      description: '长文本处理',
    },
  ];

  // ========================================================================
  // 复制到剪贴板功能
  // ========================================================================
  const copyToClipboard = async (text, messageId) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (error) {
      console.error('复制失败:', error);
    }
  };

  // ========================================================================
  // 状态轮询函数
  // ========================================================================
  const checkPdfStatus = async (pdfId) => {
    try {
      const response = await fetch(`/api/pdf/status?id=${pdfId}`);
      const result = await response.json();

      log.debug('状态查询结果:', result);

      if (result.success) {
        setPdfStatus((prev) => ({
          ...prev,
          [pdfId]: result.data.status,
        }));

        return result.data.status;
      }
    } catch (error) {
      console.error('查询状态失败:', error);
    }
    return null;
  };

  // ========================================================================
  // 权限检查
  // ========================================================================
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  // ========================================================================
  // 修改点 3：添加获取 PDF 列表的 useEffect
  // ========================================================================
  useEffect(() => {
    const fetchPdfList = async () => {
      try {
        setIsLoadingList(true);

        const response = await fetch('/api/pdf/list', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        log.debug('API 响应状态:', response.status);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        log.debug('获取到的 PDF 列表:', result);

        if (result.success) {
          // 转换数据格式，添加状态字段
          const formattedPdfFiles = result.data.map((pdf) => ({
            id: pdf.id,
            name: pdf.name || pdf.fileName,
            size: pdf.size,
            url: pdf.filePath,
            uploadedAt: new Date(pdf.createdAt),
            status: pdf.status, //保存状态
          }));

          setPdfFiles(formattedPdfFiles);
          log.debug('PDF 列表设置成功，数量:', formattedPdfFiles.length);

          // 初始化状态映射
          const statusMap = {};
          formattedPdfFiles.forEach((pdf) => {
            statusMap[pdf.id] = pdf.status;
          });
          setPdfStatus(statusMap);

          // 如果有文件且没有选中的 PDF，自动选中第一个
          if (formattedPdfFiles.length > 0 && !currentPdf) {
            setCurrentPdf(formattedPdfFiles[0]);
            log.debug('自动选中第一个 PDF:', formattedPdfFiles[0].name);
          }
        } else {
          console.error('API 返回失败:', result.error);
          setPdfFiles([]);
        }
      } catch (error) {
        console.error('获取 PDF 列表失败:', error);
        setPdfFiles([]);
      } finally {
        setIsLoadingList(false);
      }
    };

    // 只在用户登录后获取列表
    if (session?.user) {
      fetchPdfList();
    }
  }, [session]); // 依赖 session，当用户登录状态改变时重新获取

  // ========================================================================
  // 修改点 4：添加刷新列表的函数
  // ========================================================================
  const refreshPdfList = async () => {
    try {
      log.debug('刷新 PDF 列表...');
      setIsLoadingList(true);

      const response = await fetch('/api/pdf/list');
      const result = await response.json();

      if (result.success) {
        const formattedPdfFiles = result.data.map((pdf) => ({
          id: pdf.id,
          name: pdf.name || pdf.fileName,
          size: pdf.size,
          url: pdf.filePath,
          uploadedAt: new Date(pdf.createdAt),
        }));

        setPdfFiles(formattedPdfFiles);
        log.debug('列表刷新成功，数量:', formattedPdfFiles.length);
      }
    } catch (error) {
      console.error('刷新列表失败:', error);
    } finally {
      setIsLoadingList(false);
    }
  };

  // ========================================================================
  // 自动滚动到底部
  // ========================================================================
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ========================================================================
  // 点击外部关闭下拉菜单
  // ========================================================================
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        modelDropdownRef.current &&
        !modelDropdownRef.current.contains(event.target)
      ) {
        setShowModelDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ========================================================================
  // 修改点 5：修改文件上传处理函数，上传成功后刷新列表
  // ========================================================================
  const handleFileUpload = async (file) => {
    log.debug('开始上传文件:', file.name);

    // 清空之前的提示信息
    setUploadError('');
    setUploadSuccess('');

    // 验证文件类型
    if (file.type !== 'application/pdf') {
      const errorMsg = '仅支持 PDF 文件上传';
      setUploadError(errorMsg);
      console.error('错误：', errorMsg);
      return;
    }

    // 验证文件大小（最大 20MB，与后端一致）
    if (file.size > 20 * 1024 * 1024) {
      const errorMsg = '文件大小不能超过 20MB';
      setUploadError(errorMsg);
      console.error('错误：', errorMsg);
      return;
    }

    setIsUploading(true);

    try {
      // 使用 pdfApi.upload() 上传文件
      const result = await pdfApi.upload(file);

      log.debug('上传成功:', result);

      //上传成功后的处理
      if (result.success) {
        const uploadedPdf = {
          id: result.data.id,
          name: result.data.name,
          size: result.data.size,
          url: result.data.filePath,
          uploadedAt: new Date(result.data.createdAt || Date.now()),
          status: result.data.status || 'processing', // 新增：保存状态
        };

        //初始化状态
        setPdfStatus((prev) => ({
          ...prev,
          [uploadedPdf.id]: uploadedPdf.status,
        }));

        // 刷新列表
        await refreshPdfList();

        // 设置为当前 PDF
        setCurrentPdf(uploadedPdf);

        // 清空聊天记录
        setMessages([]);

        // 启动状态轮询
        if (uploadedPdf.status === 'processing') {
          setUploadSuccess('文件上传成功，正在处理中...');

          const pollInterval = setInterval(async () => {
            const status = await checkPdfStatus(uploadedPdf.id);

            log.debug('轮询状态:', status);

            if (status === 'ready' || status === 'failed') {
              clearInterval(pollInterval);

              if (status === 'ready') {
                setUploadSuccess('文件处理完成，可以开始对话！');
                log.debug('PDF 处理完成');
              } else {
                setUploadError('文件处理失败，请重新上传');
                console.error('❌ PDF 处理失败');
              }

              // 刷新列表
              await refreshPdfList();
            }
          }, 2000); // 每 2 秒检查一次

          // 5 分钟后停止轮询
          setTimeout(() => {
            clearInterval(pollInterval);
            log.debug('轮询超时，停止检查');
          }, 300000);
        } else {
          setUploadSuccess('文件上传成功！');
        }

        log.debug('文件上传成功:', uploadedPdf);

        // 3秒后自动清除成功提示（如果不是 processing 状态）
        if (uploadedPdf.status !== 'processing') {
          setTimeout(() => {
            setUploadSuccess('');
          }, 3000);
        }
      }
    } catch (error) {
      console.error('❌ 上传失败:', error);
      setUploadError(error.message || '文件上传失败，请稍后重试');
    } finally {
      setIsUploading(false);
    }
  };

  // ========================================================================
  // 文件选择处理
  // ========================================================================
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  // ========================================================================
  // 拖拽上传处理
  // ========================================================================
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  // ========================================================================
  // 修改点 6：修改 URL 上传处理，成功后刷新列表
  // ========================================================================
  const handleUrlUpload = async () => {
    if (!urlInput.trim()) {
      setUploadError('请输入 PDF 链接');
      return;
    }

    setUploadError('');
    setUploadSuccess('');
    setIsUploading(true);

    try {
      const response = await fetch('/api/upload/pdf-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput }),
      });

      const result = await response.json();

      if (result.success) {
        // 修改点：上传成功后刷新列表
        await refreshPdfList();

        const newPdf = {
          id: result.data.id || Date.now().toString(),
          name: result.data.filename || result.data.name,
          size: result.data.size,
          url: result.data.url || result.data.filePath,
          uploadedAt: new Date(),
        };

        setCurrentPdf(newPdf);
        setMessages([]);
        setShowUrlInput(false);
        setUrlInput('');

        setUploadSuccess('文件上传成功！');
        setTimeout(() => setUploadSuccess(''), 3000);
      } else {
        setUploadError(result.error || '文件上传失败');
      }
    } catch (error) {
      console.error('上传失败:', error);
      setUploadError('文件上传失败，请稍后重试');
    } finally {
      setIsUploading(false);
    }
  };

  // ========================================================================
  // handleSendMessage 函数
  // ========================================================================
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    if (!currentPdf) {
      setUploadError('请先上传 PDF 文件');
      return;
    }

    // 检查处理状态
    const status = pdfStatus[currentPdf.id] || currentPdf.status;

    if (status === 'processing') {
      setUploadError('PDF 正在处理中，请稍后再试');
      return;
    }

    if (status === 'failed') {
      setUploadError('PDF 处理失败，请重新上传');
      return;
    }

    if (status !== 'ready') {
      // 主动查询最新状态
      const latestStatus = await checkPdfStatus(currentPdf.id);

      if (latestStatus === 'processing') {
        setUploadError('PDF 正在处理中，请稍后再试');
        return;
      }

      if (latestStatus === 'failed') {
        setUploadError('PDF 处理失败，请重新上传');
        return;
      }

      if (latestStatus !== 'ready') {
        setUploadError('PDF 状态异常，请刷新页面或重新上传');
        return;
      }
    }

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsGenerating(true);

    try {
      log.debug('发送请求到 /api/chat-pdf');
      log.debug('请求参数:', {
        message: inputMessage,
        pdfId: currentPdf.id,
      });

      // 修复：使用正确的参数格式
      const response = await fetch('/api/chat-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputMessage,
          pdfId: currentPdf.id, // 使用 pdfId 而不是 pdfUrl
        }),
      });

      log.debug('收到响应状态:', response.status);

      if (!response.ok) {
        throw new Error(`API 请求失败: ${response.status}`);
      }

      const data = await response.json();
      log.debug('响应数据:', data);

      // 处理响应
      if (data.success) {
        const aiMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, aiMessage]);
        log.debug('消息添加成功');
      } else {
        throw new Error(data.error || '未知错误');
      }
    } catch (error) {
      console.error('❌ 发送消息失败:', error);

      const errorMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `抱歉，发生了错误：${error.message}`,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
      setUploadError(`发送消息失败：${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // ========================================================================
  // 切换 PDF
  // ========================================================================
  const handleSelectPdf = (pdf) => {
    setCurrentPdf(pdf);
    setMessages([]);
    setUploadError('');
    setUploadSuccess('');
  };

  // ========================================================================
  // 删除 PDF，删除后刷新列表
  // ========================================================================
  const handleDeletePdf = async (pdfId) => {
    if (!confirm('确定要删除这个 PDF 文件吗？')) {
      return;
    }

    try {
      log.debug('开始删除 PDF:', pdfId);

      // 调用后端 API 删除文件（如果有的话）
      const response = await fetch(`/api/pdf/delete`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: pdfId }),
      });

      if (response.ok) {
        log.debug('后端删除成功');
      } else {
        log.debug('⚠️后端删除失败，但继续前端删除');
      }

      // 刷新列表
      await refreshPdfList();

      // 如果删除的是当前 PDF，清空状态
      if (currentPdf?.id === pdfId) {
        setCurrentPdf(null);
        setMessages([]);
      }

      log.debug('PDF 删除成功:', pdfId);
    } catch (error) {
      console.error('❌ 删除失败:', error);
      setUploadError('删除失败，请稍后重试');
    }
  };

  // ========================================================================
  // 格式化文件大小
  // ========================================================================
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  // ========================================================================
  // 格式化日期
  // ========================================================================
  const formatDate = (date) => {
    const d = new Date(date);
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const year = d.getFullYear();
    return `${month}/${day}/${year}`;
  };

  // ========================================================================
  // 处理键盘事件（Enter 发送）
  // ========================================================================
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ========================================================================
  // 渲染
  // ========================================================================
  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* ====================================================================
          左侧边栏 - PDF 文件列表（保持不变）
      ==================================================================== */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* 修改点 9：修改头部，添加刷新按钮 */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => router.push('/')}
              className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              <span className="font-medium">返回主页</span>
            </button>

            {/* 添加刷新按钮 */}
            <button
              onClick={refreshPdfList}
              disabled={isLoadingList}
              className="p-2 text-gray-600 hover:text-gray-900 transition-colors rounded-lg hover:bg-gray-100 disabled:opacity-50"
              title="刷新列表"
            >
              <RefreshCw
                className={`w-4 h-4 ${isLoadingList ? 'animate-spin' : ''}`}
              />
            </button>
          </div>

          <h1 className="text-xl font-bold text-gray-900 flex items-center">
            <FileText className="w-6 h-6 mr-2 text-red-500" />
            PDF 工具
          </h1>
        </div>

        {/* 修改点 10：修改 PDF 文件列表，添加加载状态 */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-500">最近使用</h2>
            {isLoadingList && (
              <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
            )}
          </div>

          {isLoadingList ? (
            /* 加载状态 */
            <div className="text-center text-gray-400 text-sm mt-8">
              <Loader2 className="w-8 h-8 mx-auto mb-2 animate-spin" />
              <p>加载中...</p>
            </div>
          ) : pdfFiles.length === 0 ? (
            <div className="text-center text-gray-400 text-sm mt-8">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>暂无 PDF 文件</p>
            </div>
          ) : (
            <div className="space-y-2">
              {pdfFiles.map((pdf) => (
                <div
                  key={pdf.id}
                  onClick={() => handleSelectPdf(pdf)}
                  className={`group relative p-3 rounded-lg cursor-pointer transition-all ${
                    currentPdf?.id === pdf.id
                      ? 'bg-blue-50 border-2 border-blue-500'
                      : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                  }`}
                >
                  <div className="flex items-start">
                    <FileText
                      className={`w-5 h-5 mr-2 flex-shrink-0 ${
                        currentPdf?.id === pdf.id
                          ? 'text-blue-600'
                          : 'text-red-500'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <p
                        className="text-sm font-medium text-gray-900 truncate"
                        title={pdf.name}
                      >
                        {pdf.name}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatFileSize(pdf.size)}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {formatDate(pdf.uploadedAt)}
                      </p>

                      {/* 新增状态标签 */}
                      {pdfStatus[pdf.id] === 'processing' && (
                        <div className="flex items-center mt-1">
                          <Loader2 className="w-3 h-3 mr-1 animate-spin text-blue-500" />
                          <span className="text-xs text-blue-600">
                            处理中...
                          </span>
                        </div>
                      )}

                      {pdfStatus[pdf.id] === 'failed' && (
                        <div className="flex items-center mt-1">
                          <X className="w-3 h-3 mr-1 text-red-500" />
                          <span className="text-xs text-red-600">处理失败</span>
                        </div>
                      )}

                      {pdfStatus[pdf.id] === 'ready' && (
                        <div className="flex items-center mt-1">
                          <Check className="w-3 h-3 mr-1 text-green-500" />
                          <span className="text-xs text-green-600">就绪</span>
                        </div>
                      )}
                    </div>

                    {/* 状态指示器（右上角） */}
                    {pdfStatus[pdf.id] === 'processing' && (
                      <div className="absolute top-2 right-2">
                        <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                      </div>
                    )}

                    {pdfStatus[pdf.id] === 'failed' && (
                      <div className="absolute top-2 right-2">
                        <X className="w-4 h-4 text-red-500" />
                      </div>
                    )}

                    {/* 删除按钮 */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeletePdf(pdf.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                    >
                      <X className="w-4 h-4 text-gray-400 hover:text-red-500" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ====================================================================
          右侧主内容区
      ==================================================================== */}
      <div className="flex-1 flex flex-col">
        {/* 顶部工具栏（保持不变） */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between max-w-5xl mx-auto">
            {/* 左侧：标题和图标 */}
            <div className="flex items-center">
              <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-pink-500 rounded-xl flex items-center justify-center mr-3 shadow-lg">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  在线 ChatPDF
                </h1>
                <p className="text-sm text-gray-500">
                  使用 Chat AI 能力帮助你更好的阅读
                </p>
              </div>
            </div>

            {/* 右侧：模型选择下拉菜单 */}
            <div className="relative" ref={modelDropdownRef}>
              <button
                onClick={() => setShowModelDropdown(!showModelDropdown)}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                <span className="text-2xl">
                  {models.find((m) => m.id === selectedModel)?.icon}
                </span>
                <span className="font-medium text-gray-900">
                  {models.find((m) => m.id === selectedModel)?.name}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-gray-500 transition-transform ${
                    showModelDropdown ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {/* 下拉菜单 */}
              {showModelDropdown && (
                <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50">
                  {models.map((model) => (
                    <button
                      key={model.id}
                      onClick={() => {
                        setSelectedModel(model.id);
                        setShowModelDropdown(false);
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-start ${
                        selectedModel === model.id ? 'bg-blue-50' : ''
                      }`}
                    >
                      <span className="text-2xl mr-3">{model.icon}</span>
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">
                          {model.name}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          {model.description}
                        </div>
                      </div>
                      {selectedModel === model.id && (
                        <div className="w-2 h-2 bg-blue-600 rounded-full mt-2"></div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 主内容区 */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="max-w-5xl mx-auto p-6">
            {/* 修改点 11：添加错误和成功提示 */}
            {uploadError && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <X className="w-5 h-5 text-red-500 mr-3 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-red-800 font-medium">上传失败</p>
                  <p className="text-sm text-red-600 mt-1">{uploadError}</p>
                </div>
                <button
                  onClick={() => setUploadError('')}
                  className="text-red-400 hover:text-red-600 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {uploadSuccess && (
              <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start">
                <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center mr-3 flex-shrink-0 mt-0.5">
                  <svg
                    className="w-3 h-3 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-green-800 font-medium">上传成功</p>
                  <p className="text-sm text-green-600 mt-1">{uploadSuccess}</p>
                </div>
                <button
                  onClick={() => setUploadSuccess('')}
                  className="text-green-400 hover:text-green-600 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {!currentPdf ? (
              /* ============================================================
                  无 PDF 时显示上传区域（保持不变）
              ============================================================ */
              <div className="flex items-center justify-center min-h-[500px]">
                <div className="w-full max-w-2xl">
                  {/* 拖拽上传区域 */}
                  <div
                    ref={dropZoneRef}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
                      isDragging
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-300 bg-white hover:border-gray-400'
                    }`}
                  >
                    <div className="w-20 h-20 bg-gradient-to-br from-red-500 to-pink-500 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                      <FileText className="w-10 h-10 text-white" />
                    </div>

                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      上传 PDF 文件
                    </h3>
                    <p className="text-gray-500 mb-6">点击或拖拽到此处上传</p>

                    {/* 上传按钮 */}
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isUploading}
                      className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed mb-4"
                    >
                      {isUploading ? (
                        <>
                          <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                          上传中...
                        </>
                      ) : (
                        <>
                          <Upload className="w-5 h-5 mr-2" />
                          选择文件上传
                        </>
                      )}
                    </button>

                    {/* 隐藏的文件输入 */}
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,application/pdf"
                      onChange={handleFileSelect}
                      className="hidden"
                    />

                    {/* URL 上传按钮 */}
                    <div className="mt-4">
                      {!showUrlInput ? (
                        <button
                          onClick={() => setShowUrlInput(true)}
                          className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
                        >
                          <LinkIcon className="w-4 h-4 mr-2" />
                          使用链接上传
                        </button>
                      ) : (
                        <div className="flex items-center space-x-2 max-w-md mx-auto">
                          <input
                            type="url"
                            value={urlInput}
                            onChange={(e) => setUrlInput(e.target.value)}
                            placeholder="输入 PDF 链接"
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          <button
                            onClick={handleUrlUpload}
                            disabled={isUploading}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                          >
                            上传
                          </button>
                          <button
                            onClick={() => {
                              setShowUrlInput(false);
                              setUrlInput('');
                            }}
                            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                          >
                            取消
                          </button>
                        </div>
                      )}
                    </div>

                    {/* 提示信息 */}
                    <p className="text-sm text-gray-400 mt-6">
                      支持的文件类型: <span className="font-medium">PDF</span> |
                      最大文件大小: <span className="font-medium">20MB</span>
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              /* ============================================================
                  有 PDF 时显示聊天界面 - 添加 Markdown 和复制功能
              ============================================================ */
              <div className="flex flex-col h-full">
                {/* 当前 PDF 信息 */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
                  <div className="flex items-center">
                    <FileText className="w-6 h-6 text-red-500 mr-3" />
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">
                        {currentPdf.name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {formatFileSize(currentPdf.size)} •{' '}
                        {formatDate(currentPdf.uploadedAt)}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        setCurrentPdf(null);
                        setMessages([]);
                        setUploadError('');
                        setUploadSuccess('');
                      }}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* 聊天消息区域 */}
                <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 mb-4 overflow-hidden flex flex-col">
                  {messages.length === 0 ? (
                    /* 空状态 */
                    <div className="flex-1 flex items-center justify-center p-8">
                      <div className="text-center">
                        <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                          <FileText className="w-8 h-8 text-white" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                          开始与 PDF 对话
                        </h3>
                        <p className="text-gray-500 mb-4">
                          问我关于这个 PDF 的任何问题
                        </p>
                        <div className="flex flex-wrap gap-2 justify-center">
                          <button
                            onClick={() =>
                              setInputMessage('这个文档的主要内容是什么？')
                            }
                            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
                          >
                            📄 文档主要内容
                          </button>
                          <button
                            onClick={() =>
                              setInputMessage('请总结这个文档的关键要点')
                            }
                            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
                          >
                            ✨ 总结关键要点
                          </button>
                          <button
                            onClick={() =>
                              setInputMessage(
                                '这个文档中有哪些重要的数据或统计信息？'
                              )
                            }
                            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
                          >
                            📊 数据统计
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* 消息列表 - 添加 Markdown 渲染和复制功能 */
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                      {messages.map((message) => (
                        <div
                          key={message.id}
                          className={`mb-6 flex ${
                            message.role === 'user'
                              ? 'justify-end'
                              : 'justify-start'
                          }`}
                        >
                          <div
                            className={`max-w-3xl rounded-2xl px-6 py-4 relative group ${
                              message.role === 'user'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-900'
                            }`}
                          >
                            {/* 复制按钮（仅 AI 消息显示） */}
                            {message.role === 'assistant' && (
                              <button
                                onClick={() =>
                                  copyToClipboard(message.content, message.id)
                                }
                                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-gray-200 rounded-lg"
                                title="复制消息"
                              >
                                {copiedMessageId === message.id ? (
                                  <Check className="w-4 h-4 text-green-500" />
                                ) : (
                                  <Copy className="w-4 h-4 text-gray-400" />
                                )}
                              </button>
                            )}

                            {/* 消息内容渲染 */}
                            <div className="pr-8">
                              {message.role === 'user' ? (
                                /* 用户消息：普通文本 */
                                <div className="whitespace-pre-wrap break-words">
                                  {message.content}
                                </div>
                              ) : (
                                /* AI 消息：Markdown 渲染 */
                                <div
                                  className="prose prose-sm max-w-none prose-slate
                                  prose-headings:text-gray-900 prose-headings:font-semibold prose-headings:mb-3
                                  prose-p:text-gray-700 prose-p:leading-relaxed prose-p:mb-4
                                  prose-strong:text-gray-900 prose-strong:font-semibold
                                  prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-2 prose-code:py-1 prose-code:rounded prose-code:text-sm
                                  prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:p-4 prose-pre:rounded-lg prose-pre:overflow-x-auto
                                  prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:py-3 prose-blockquote:px-4 prose-blockquote:rounded-r-lg prose-blockquote:my-4
                                  prose-ul:text-gray-700 prose-ul:mb-4 prose-ol:text-gray-700 prose-ol:mb-4
                                  prose-li:text-gray-700 prose-li:my-1 prose-li:leading-relaxed
                                  prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
                                  prose-table:border-collapse prose-table:border prose-table:border-gray-300
                                  prose-th:border prose-th:border-gray-300 prose-th:bg-gray-50 prose-th:px-4 prose-th:py-2 prose-th:text-left prose-th:font-semibold
                                  prose-td:border prose-td:border-gray-300 prose-td:px-4 prose-td:py-2"
                                >
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {message.content}
                                  </ReactMarkdown>
                                </div>
                              )}
                            </div>

                            {/* 新增：时间戳 */}
                            <div
                              className={`text-xs mt-2 ${
                                message.role === 'user'
                                  ? 'text-blue-100'
                                  : 'text-gray-400'
                              }`}
                            >
                              {new Date(message.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* 加载动画 */}
                      {isGenerating && (
                        <div className="mb-6 flex justify-start">
                          <div className="max-w-3xl rounded-2xl px-6 py-4 bg-gray-100">
                            <div className="flex items-center space-x-2">
                              <div
                                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                style={{ animationDelay: '0ms' }}
                              ></div>
                              <div
                                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                style={{ animationDelay: '150ms' }}
                              ></div>
                              <div
                                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                style={{ animationDelay: '300ms' }}
                              ></div>
                            </div>
                          </div>
                        </div>
                      )}

                      <div ref={messagesEndRef} />
                    </div>
                  )}
                </div>

                {/* 输入区域（保持不变） */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                  <div className="flex items-end space-x-3">
                    <textarea
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="输入你的问题..."
                      rows={1}
                      className="flex-1 resize-none px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      style={{ minHeight: '52px', maxHeight: '150px' }}
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={!inputMessage.trim() || isGenerating}
                      className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                      style={{ minHeight: '52px' }}
                    >
                      {isGenerating ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Send className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
