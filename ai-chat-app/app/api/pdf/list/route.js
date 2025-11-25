/**
 * ============================================================================
 * PDF 列表 API (app/api/pdf/list/route.js)
 * ============================================================================
 *
 * 功能：获取当前用户的 PDF 文件列表
 *
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
      return NextResponse.json(
        { success: false, error: '未登录' },
        { status: 401 }
      );
    }

    // 查询用户的 PDF 列表
    const pdfFiles = await prisma.PDF.findMany({
      where: {
        userId: session.user.id,
      },
      orderBy: {
        createdAt: 'desc',
      },
      select: {
        id: true,
        name: true,
        fileName: true,
        filePath: true,
        size: true,
        createdAt: true,
      },
    });

    return NextResponse.json({
      success: true,
      data: pdfFiles,
    });
  } catch (error) {
    console.error('获取 PDF 列表失败:', error);
    return NextResponse.json(
      { success: false, error: '获取列表失败' },
      { status: 500 }
    );
  }
}
