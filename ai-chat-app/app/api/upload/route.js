/**
 * ============================================================================
 * 文件上传 API (app/api/upload/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   处理文件上传请求，将图片保存到服务器本地目录
 *
 * 主要功能：
 *   1. 接收 FormData 格式的文件
 *   2. 验证文件类型和大小
 *   3. 生成唯一文件名并保存到本地
 *   4. 返回文件的完整访问 URL
 *
 * 路由：POST /api/upload
 *
 * 存储路径：
 *   public/uploads/images/{年份}/{月份}/{时间戳}_{随机字符串}.{扩展名}
 *   例如：public/uploads/images/2024/01/1704067200000_abc123.jpg
 *
 * 访问 URL：
 *   http://localhost:3000/uploads/images/2024/01/1704067200000_abc123.jpg
 *
 * ============================================================================
 */
import { mkdir, writeFile, access } from 'fs/promises'; //  使用 ES modules
import { existsSync, statSync } from 'fs'; //  导入同步方法
import { join } from 'path'; // 路径拼接工具
import { NextResponse } from 'next/server';
import log from '@/lib/log';

/**
 * POST - 文件上传接口
 *
 * 请求格式：multipart/form-data
 * 请求体：
 *   - file: File（文件对象）
 *
 * 限制：
 *   - 文件大小：最大 10MB
 *   - 文件类型：只支持图片（image/*）
 *
 * 响应：
 *   {
 *     success: true,
 *     data: {
 *       url: string,       // 完整访问 URL
 *       filename: string,  // 原始文件名
 *       size: number,      // 文件大小（字节）
 *       mimeType: string   // MIME 类型
 *     }
 *   }
 */
export async function POST(req) {
  try {
    // ========================================================================
    // 1. 解析 FormData 并获取文件
    // ========================================================================
    const formData = await req.formData();
    const file = formData.get('file'); // 获取名为 'file' 的字段

    if (!file) {
      return NextResponse.json(
        { error: '没有上传文件' },
        { status: 400 } // 400 Bad Request
      );
    }

    // ========================================================================
    // 2. 验证文件大小（最大 10MB）
    // ========================================================================
    if (file.size > 10 * 1024 * 1024) {
      return NextResponse.json(
        { error: '文件大小超过 10MB 限制' },
        { status: 400 }
      );
    }

    // ========================================================================
    // 3. 验证文件类型（只允许图片）
    // ========================================================================
    if (!file.type.startsWith('image/')) {
      return NextResponse.json({ error: '只支持图片文件' }, { status: 400 });
    }

    // ========================================================================
    // 4. 读取文件内容
    // ========================================================================
    const bytes = await file.arrayBuffer(); // 读取为 ArrayBuffer
    const buffer = Buffer.from(bytes); // 转换为 Node.js Buffer

    // ========================================================================
    // 5. 生成唯一文件名
    // ========================================================================
    const timestamp = Date.now(); // 时间戳（毫秒）
    const randomString = Math.random().toString(36).substring(7); // 随机字符串（7位）
    const ext = file.name.split('.').pop(); // 文件扩展名
    const filename = `${timestamp}_${randomString}.${ext}`; // 最终文件名
    // 示例：1704067200000_abc123.jpg

    // ========================================================================
    // 6. 创建目录结构（按年月分类）
    // ========================================================================
    const year = new Date().getFullYear(); // 年份（如：2024）
    const month = String(new Date().getMonth() + 1).padStart(2, '0'); // 月份（如：01）
    const uploadDir = join(
      process.cwd(), // 项目根目录
      'public', // public 目录
      'uploads', // uploads 目录
      'images', // images 目录
      String(year), // 年份目录
      month // 月份目录
    );
    // 示例：/path/to/project/public/uploads/images/2024/01
    //  调试日志
    log.debug(' 上传目录:', uploadDir);
    log.debug(' 当前工作目录:', process.cwd());

    // 确保目录存在（递归创建）
    await mkdir(uploadDir, { recursive: true });

    // ========================================================================
    // 7. 保存文件到磁盘
    // ========================================================================
    const filepath = join(uploadDir, filename); // 完整文件路径
    log.debug(' 文件路径:', filepath);
    await writeFile(filepath, buffer); // 写入文件
    //  验证文件是否真的保存了（使用同步方法）
    const exists = existsSync(filepath);
    log.debug(' 文件是否存在:', exists);

    if (exists) {
      //  检查目录权限
      const stats = statSync(uploadDir);
      log.debug(' 目录权限:', stats.mode.toString(8));
      log.debug(' 文件大小:', statSync(filepath).size, 'bytes');
    } else {
      console.error(' 文件保存失败，文件不存在');
    }

    // ========================================================================
    // 8. 生成访问 URL
    // ========================================================================
    // 相对路径（相对于 public 目录）
    // 相对路径（通过 API 路由访问）
    const url = `/api/files/uploads/images/${year}/${month}/${filename}`;
    //const url = `/uploads/images/${year}/${month}/${filename}`;

    // 完整 URL（包含域名）
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    const fullUrl = `${baseUrl}${url}`;
    // 示例：http://localhost:3000/uploads/images/2024/01/1704067200000_abc123.jpg

    // ========================================================================
    // 9. 返回成功响应
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: {
        url: fullUrl, // 完整访问 URL
        filename: file.name, // 原始文件名
        size: file.size, // 文件大小（字节）
        mimeType: file.type, // MIME 类型（如：image/jpeg）
      },
    });
  } catch (error) {
    // ========================================================================
    // 错误处理
    // ========================================================================
    console.error('文件上传失败:', error);
    return NextResponse.json(
      { error: '文件上传失败' },
      { status: 500 } // 500 Internal Server Error
    );
  }
}
