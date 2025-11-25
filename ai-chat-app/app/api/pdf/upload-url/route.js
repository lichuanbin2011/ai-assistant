/**
 * ============================================================================
 * PDF URL 上传 API (app/api/pdf/upload-url/route.js)
 * ============================================================================
 *
 * 功能：从 URL 下载 PDF 文件并保存
 *
 * ============================================================================
 */
import { NextResponse } from 'next/server';
import { auth } from '@/app/api/auth/[...nextauth]/route';
import { prisma } from '@/lib/prisma';
import { promises as fs } from 'fs';
import path from 'path';

export async function POST(req) {
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
    const { url } = await req.json();

    if (!url) {
      return NextResponse.json(
        { success: false, error: '未提供 URL' },
        { status: 400 }
      );
    }

    // 验证 URL 格式
    let pdfUrl;
    try {
      pdfUrl = new URL(url);
    } catch (e) {
      return NextResponse.json(
        { success: false, error: 'URL 格式不正确' },
        { status: 400 }
      );
    }

    // 下载文件
    const response = await fetch(url);

    if (!response.ok) {
      return NextResponse.json(
        { success: false, error: '无法下载文件' },
        { status: 400 }
      );
    }

    // 验证内容类型
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('pdf')) {
      return NextResponse.json(
        { success: false, error: '链接不是 PDF 文件' },
        { status: 400 }
      );
    }

    // 获取文件内容
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // 验证文件大小
    if (buffer.length > 20 * 1024 * 1024) {
      return NextResponse.json(
        { success: false, error: '文件大小不能超过 20MB' },
        { status: 400 }
      );
    }

    // 生成文件名
    const timestamp = Date.now();
    const urlPath = pdfUrl.pathname;
    const originalName = path.basename(urlPath) || 'document.pdf';
    const ext = path.extname(originalName) || '.pdf';
    const baseName = path.basename(originalName, ext);
    const fileName = `${baseName}_${timestamp}${ext}`;

    // 创建上传目录
    const uploadDir = path.join(
      process.cwd(),
      'public',
      'uploads',
      'pdfs',
      new Date().getFullYear().toString(),
      (new Date().getMonth() + 1).toString()
    );
    await fs.mkdir(uploadDir, { recursive: true });

    // 保存文件
    const filePath = path.join(uploadDir, fileName);
    await fs.writeFile(filePath, buffer);

    // 生成访问 URL
    const fileUrl = `/uploads/pdfs/${new Date().getFullYear()}/${new Date().getMonth() + 1}/${fileName}`;

    // 保存到数据库
    const pdfRecord = await prisma.pDF.create({
      data: {
        userId: session.user.id,
        name: originalName,
        fileName: fileName,
        filePath: fileUrl,
        size: buffer.length,
      },
    });

    return NextResponse.json({
      success: true,
      message: '上传成功',
      data: pdfRecord,
    });
  } catch (error) {
    console.error('PDF URL 上传失败:', error);
    return NextResponse.json(
      { success: false, error: '上传失败，请稍后重试' },
      { status: 500 }
    );
  }
}
