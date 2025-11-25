/**
 * ============================================================================
 * PDF 删除 API (app/api/pdf/delete/route.js)
 * ============================================================================
 *
 * 功能：删除 PDF 文件（数据库记录和物理文件）
 *
 * ============================================================================
 */
import { NextResponse } from 'next/server';
import { auth } from '@/app/api/auth/[...nextauth]/route';
import { prisma } from '@/lib/prisma';
import { promises as fs } from 'fs';
import path from 'path';

export async function DELETE(req) {
  try {
    // 身份验证
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { success: false, error: '未登录' },
        { status: 401 }
      );
    }

    // 解析请求体
    //  修复点 1：解析请求体，支持 id 和 pdfId 两种参数名
    const body = await req.json();
    console.log(' 请求体:', body);

    const pdfId = body.id || body.pdfId; // 支持两种参数名

    if (!pdfId) {
      return NextResponse.json(
        { success: false, error: '未提供 PDF ID' },
        { status: 400 }
      );
    }

    // 查询 PDF 记录
    const pdf = await prisma.PDF.findUnique({
      where: { id: pdfId },
    });

    if (!pdf) {
      return NextResponse.json(
        { success: false, error: 'PDF 不存在' },
        { status: 404 }
      );
    }

    // 验证权限
    if (pdf.userId !== session.user.id) {
      return NextResponse.json(
        { success: false, error: '无权删除此文件' },
        { status: 403 }
      );
    }

    // 删除物理文件
    try {
      const filePath = path.join(process.cwd(), 'public', pdf.filePath);
      await fs.unlink(filePath);
    } catch (error) {
      console.error('删除物理文件失败:', error);
      // 继续删除数据库记录
    }

    // 删除数据库记录
    await prisma.PDF.delete({
      where: { id: pdfId },
    });

    return NextResponse.json({
      success: true,
      message: '删除成功',
    });
  } catch (error) {
    console.error('删除 PDF 失败:', error);
    return NextResponse.json(
      { success: false, error: '删除失败，请稍后重试' },
      { status: 500 }
    );
  }
}
