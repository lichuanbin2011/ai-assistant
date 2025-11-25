/**
 * ============================================================================
 * PDF 上传 API 路由 (app/api/upload/route.js)
 * ============================================================================
 *
 * 修改记录：
 *   - 2025-01-XX：集成 Python RAG Service，移除本地处理逻辑
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
// 🆕 调用 Python RAG Service 上传 PDF
// ============================================================================
async function uploadToPythonService(file, userId) {
  try {
    log.debug('调用 Python RAG Service 上传 PDF');
    log.debug(`  - 文件名: ${file.name}`);
    log.debug(`  - 文件大小: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
    log.debug(`  - 用户ID: ${userId}`);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);

    const response = await fetch(`${RAG_SERVICE_URL}/api/v1/pdf/upload`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(120000), // 2 分钟超时
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Python 服务错误 (${response.status})`
      );
    }

    const data = await response.json();
    log.debug('Python RAG Service 响应:', data);

    return data;
  } catch (error) {
    console.error('❌ Python RAG Service 调用失败:', error);
    throw error;
  }
}

// ============================================================================
// 🔄 降级：本地处理（如果 Python 服务不可用）
// ============================================================================
async function uploadLocally(file, userId) {
  log.debug('降级：使用本地处理');

  // 注意：这里保留原有的本地处理逻辑作为降级方案
  // 如果您完全信任 Python 服务，可以删除此函数

  const { prisma } = await import('@/lib/prisma');
  const fs = await import('fs');
  const path = await import('path');

  // 保存文件
  const uploadDir = path.join(process.cwd(), 'uploads');
  if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
  }

  const fileName = `${Date.now()}-${file.name}`;
  const filePath = path.join(uploadDir, fileName);

  const buffer = Buffer.from(await file.arrayBuffer());
  fs.writeFileSync(filePath, buffer);

  // 创建数据库记录
  const pdf = await prisma.PDF.create({
    data: {
      name: file.name,
      fileName: fileName,
      filePath: filePath,
      size: file.size,
      userId: userId,
      status: 'processing', // 标记为处理中
    },
  });

  log.debug('本地上传完成，PDF ID:', pdf.id);

  // 注意：本地处理不会自动向量化，需要手动触发
  return {
    success: true,
    data: {
      id: pdf.id,
      name: pdf.name,
      filePath: pdf.filePath,
      size: pdf.size,
      status: 'processing',
    },
    message: '文件上传成功，正在处理中...',
  };
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
    if (!session?.user?.id) {
      log.debug('❌ 用户未登录');
      return NextResponse.json(
        { success: false, error: '请先登录' },
        { status: 401 }
      );
    }

    log.debug('✅ 用户已登录:', session.user.email);

    // ========================================================================
    // 2. 解析上传文件
    // ========================================================================
    const formData = await request.formData();
    const file = formData.get('file');

    if (!file) {
      return NextResponse.json(
        { success: false, error: '未选择文件' },
        { status: 400 }
      );
    }

    // ========================================================================
    // 3. 验证文件类型
    // ========================================================================
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return NextResponse.json(
        { success: false, error: '仅支持 PDF 文件上传' },
        { status: 400 }
      );
    }

    // ========================================================================
    // 4. 验证文件大小（最大 20MB）
    // ========================================================================
    const maxSize = 20 * 1024 * 1024;
    if (file.size > maxSize) {
      return NextResponse.json(
        {
          success: false,
          error: `文件大小不能超过 ${maxSize / 1024 / 1024}MB`,
        },
        { status: 400 }
      );
    }

    log.debug('文件验证通过:', {
      name: file.name,
      size: `${(file.size / 1024 / 1024).toFixed(2)}MB`,
    });

    // ========================================================================
    // 5. 上传处理（优先使用 Python 服务）
    // ========================================================================
    let result;

    if (USE_RAG_SERVICE) {
      try {
        // 策略1：调用 Python RAG Service
        result = await uploadToPythonService(file, session.user.id);
        log.debug('✅ Python RAG Service 上传成功');
      } catch (serviceError) {
        console.warn('⚠️ Python RAG Service 不可用，降级到本地处理');
        log.debug(`降级原因: ${serviceError.message}`);

        // 策略2：降级到本地处理
        result = await uploadLocally(file, session.user.id);
      }
    } else {
      // 直接使用本地处理
      result = await uploadLocally(file, session.user.id);
    }

    // ========================================================================
    // 6. 返回响应
    // ========================================================================
    return NextResponse.json(result);
  } catch (error) {
    console.error('❌ 上传失败:', error);
    return NextResponse.json(
      {
        success: false,
        error: error.message || '上传失败，请稍后重试',
      },
      { status: 500 }
    );
  }
}

// ============================================================================
// GET 请求处理（查询上传状态）
// ============================================================================
export async function GET(request) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: '请先登录' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const pdfId = searchParams.get('id');

    if (!pdfId) {
      return NextResponse.json({ error: '缺少 PDF ID' }, { status: 400 });
    }

    // 调用 Python 服务查询状态
    if (USE_RAG_SERVICE) {
      try {
        const response = await fetch(
          `${RAG_SERVICE_URL}/api/v1/pdf/${pdfId}/status`
        );

        if (!response.ok) {
          throw new Error(`查询失败 (${response.status})`);
        }

        const data = await response.json();
        return NextResponse.json(data);
      } catch (error) {
        console.error('❌ 查询状态失败:', error);
      }
    }

    // 降级：查询本地数据库
    const { prisma } = await import('@/lib/prisma');
    const pdf = await prisma.PDF.findUnique({
      where: { id: pdfId },
      select: {
        id: true,
        name: true,
        status: true,
        totalPages: true,
        totalChunks: true,
        errorMessage: true,
      },
    });

    if (!pdf) {
      return NextResponse.json({ error: 'PDF 不存在' }, { status: 404 });
    }

    return NextResponse.json({
      success: true,
      data: {
        id: pdf.id,
        name: pdf.name,
        status: pdf.status,
        total_pages: pdf.totalPages,
        total_chunks: pdf.totalChunks,
        error_message: pdf.errorMessage,
      },
    });
  } catch (error) {
    console.error('❌ 查询状态失败:', error);
    return NextResponse.json(
      { error: '查询失败，请稍后重试' },
      { status: 500 }
    );
  }
}
