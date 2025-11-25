/**
 * ============================================================================
 * PDF 处理状态查询 API app/api/pdf/status/route.js
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { auth } from '@/app/api/auth/[...nextauth]/route';
import { prisma } from '@/lib/prisma';

export async function GET(req) {
  try {
    // 身份验证
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: '未登录' }, { status: 401 });
    }

    // 获取 PDF ID
    const { searchParams } = new URL(req.url);
    const pdfId = searchParams.get('id');

    if (!pdfId) {
      return NextResponse.json({ error: '缺少 PDF ID' }, { status: 400 });
    }

    // 查询 PDF 状态
    const pdf = await prisma.pDF.findUnique({
      where: { id: pdfId },
      select: {
        id: true,
        name: true,
        status: true,
        totalChunks: true,
        totalPages: true,
        processedAt: true,
        errorMessage: true,
      },
    });

    if (!pdf) {
      return NextResponse.json({ error: 'PDF 不存在' }, { status: 404 });
    }

    // 验证权限
    const pdfWithUser = await prisma.pDF.findUnique({
      where: { id: pdfId },
      select: { userId: true },
    });

    if (pdfWithUser.userId !== session.user.id) {
      return NextResponse.json({ error: '无权访问' }, { status: 403 });
    }

    return NextResponse.json({
      success: true,
      data: pdf,
    });
  } catch (error) {
    console.error('查询状态失败:', error);
    return NextResponse.json({ error: '查询失败' }, { status: 500 });
  }
}
