/**
 * ============================================================================
 * ChatPDF API 路由 (app/api/chat-pdf/route.js)
 * ============================================================================
 *
 * 修改记录：
 *   - 2025-01-XX：集成 Python RAG Service，移除本地 RAG 逻辑
 *
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { auth } from '@/app/api/auth/[...nextauth]/route';
import log from '@/lib/log';

// ============================================================================
// 配置
// ============================================================================
const RAG_SERVICE_URL = process.env.RAG_SERVICE_URL || 'http://rag-service:8001';
const USE_RAG_SERVICE = process.env.USE_RAG_SERVICE !== 'false'; // 默认启用

// ============================================================================
// 🆕 调用 Python RAG Service 进行对话
// ============================================================================
async function chatWithPythonService(message, pdfId, userId, model = null) {
  try {
    log.debug('调用 Python RAG Service 进行对话');
    log.debug(`  - 消息: ${message.substring(0, 50)}...`);
    log.debug(`  - PDF ID: ${pdfId}`);
    log.debug(`  - 用户ID: ${userId}`);

    const response = await fetch(`${RAG_SERVICE_URL}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        pdf_id: pdfId,
        user_id: userId,
        model: model || 'deepseek/deepseek-chat-v3.1',
      }),
      signal: AbortSignal.timeout(60000), // 60 秒超时
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Python 服务错误 (${response.status})`
      );
    }

    const data = await response.json();
    log.debug('Python RAG Service 响应成功');

    return data;
  } catch (error) {
    console.error('❌ Python RAG Service 调用失败:', error);
    throw error;
  }
}

// ============================================================================
// 🔄 降级：本地处理（如果 Python 服务不可用）
// ============================================================================
async function chatLocally(message, pdfId, userId) {
  log.debug('降级：使用本地处理（无 RAG）');

  // 注意：降级模式下不使用 RAG，仅使用基础 LLM
  // 如果需要完整的 RAG 功能，建议确保 Python 服务可用

  try {
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
        'X-Title': process.env.NEXT_PUBLIC_APP_NAME || 'AI Chat App',
      },
      body: JSON.stringify({
        model: 'deepseek/deepseek-chat-v3.1',
        messages: [
          {
            role: 'system',
            content: '你是一个 AI 助手。注意：当前处于降级模式，无法访问 PDF 文档内容。',
          },
          {
            role: 'user',
            content: message,
          },
        ],
        temperature: 0.7,
        max_tokens: 2000,
      }),
    });

    if (!response.ok) {
      throw new Error(`LLM API 错误 (${response.status})`);
    }

    const data = await response.json();
    const aiMessage = data.choices?.[0]?.message?.content;

    if (!aiMessage) {
      throw new Error('AI 响应为空');
    }

    return {
      success: true,
      response: aiMessage,
      metadata: {
        pdf_name: 'N/A',
        total_pages: null,
        total_chunks: 0,
        chunks_retrieved: 0,
        sources: [],
        model: 'deepseek/deepseek-chat-v3.1',
        rag_enabled: false, // 标识未使用 RAG
        timestamp: new Date().toISOString(),
        warning: '当前处于降级模式，无法访问 PDF 文档内容',
      },
    };
  } catch (error) {
    console.error('❌ 降级模式也失败:', error);
    throw error;
  }
}

// ============================================================================
// POST 请求处理
// ============================================================================
export async function POST(request) {
  try {
    // ========================================================================
    // 1. 身份验证
    // ========================================================================
    const session = await auth();
    if (!session || !session.user) {
      log.debug('❌ 用户未登录');
      return NextResponse.json({ error: '请先登录' }, { status: 401 });
    }

    log.debug('✅ 用户已登录:', session.user.email);

    // ========================================================================
    // 2. 解析请求参数
    // ========================================================================
    const { message, pdfId, model } = await request.json();

    if (!message?.trim()) {
      return NextResponse.json({ error: '消息不能为空' }, { status: 400 });
    }

    if (!pdfId) {
      return NextResponse.json(
        { error: '请先选择 PDF 文件' },
        { status: 400 }
      );
    }

    log.debug('请求参数:', {
      message: message.substring(0, 50) + '...',
      pdfId,
      model: model || 'default',
    });

    // ========================================================================
    // 3. 调用 RAG 服务（优先使用 Python 服务）
    // ========================================================================
    let result;

    if (USE_RAG_SERVICE) {
      try {
        // 策略1：调用 Python RAG Service
        result = await chatWithPythonService(
          message,
          pdfId,
          session.user.id,
          model
        );
        log.debug('✅ Python RAG Service 对话成功');
      } catch (serviceError) {
        console.warn('⚠️ Python RAG Service 不可用，降级到本地处理');
        log.debug(`降级原因: ${serviceError.message}`);

        // 策略2：降级到本地处理（无 RAG）
        result = await chatLocally(message, pdfId, session.user.id);
      }
    } else {
      // 直接使用本地处理
      result = await chatLocally(message, pdfId, session.user.id);
    }

    // ========================================================================
    // 4. 返回响应
    // ========================================================================
    return NextResponse.json(result);
  } catch (error) {
    console.error('❌ ChatPDF API 错误:', error);
    return NextResponse.json(
      {
        error: '服务器内部错误',
        details: error.message,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
