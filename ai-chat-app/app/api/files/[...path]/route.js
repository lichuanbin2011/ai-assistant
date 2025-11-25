/**
 * ============================================================================
 * 静态文件服务 API (app/api/files/[...path]/route.js)
 * ============================================================================
 * 用于在 standalone 模式下服务上传的文件
 */

import { NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

export async function GET(req, { params }) {
  try {
    // 获取文件路径
    const { path } = await params;
    const filepath = join(process.cwd(), 'public', ...path);

    console.log(' 请求文件:', filepath);

    // 检查文件是否存在
    if (!existsSync(filepath)) {
      console.error(' 文件不存在:', filepath);
      return new NextResponse('File not found', { status: 404 });
    }

    // 读取文件
    const file = await readFile(filepath);

    // 根据文件扩展名设置 Content-Type
    const ext = path[path.length - 1].split('.').pop().toLowerCase();
    const contentTypes = {
      png: 'image/png',
      jpg: 'image/jpeg',
      jpeg: 'image/jpeg',
      gif: 'image/gif',
      webp: 'image/webp',
      svg: 'image/svg+xml',
    };

    const contentType = contentTypes[ext] || 'application/octet-stream';

    console.log(' 返回文件:', filepath, 'Content-Type:', contentType);

    // 返回文件
    return new NextResponse(file, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });
  } catch (error) {
    console.error(' 读取文件失败:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
