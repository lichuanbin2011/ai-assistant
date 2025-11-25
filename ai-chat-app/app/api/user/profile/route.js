/**
 * ============================================================================
 * 用户资料 API (app/api/user/profile/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   处理用户个人资料的获取和更新
 *
 * 主要功能：
 *   1. GET：获取当前用户的详细资料（含统计数据）
 *   2. PATCH：更新用户名和头像
 *
 * 路由：
 *   - GET /api/user/profile
 *   - PATCH /api/user/profile
 *
 * 权限：需要登录
 *
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { auth } from '@/app/api/auth/[...nextauth]/route'; // NextAuth 认证函数

/**
 * GET - 获取用户个人资料
 *
 * 功能：
 *   - 返回用户基本信息
 *   - 返回统计数据（会话数、消息数）
 *
 * 响应：
 *   {
 *     success: true,
 *     data: {
 *       id, email, name, avatarUrl, role,
 *       createdAt, updatedAt,
 *       _count: { conversations, messages }
 *     }
 *   }
 */
export async function GET(req) {
  try {
    // ========================================================================
    // 1. 验证用户登录状态
    // ========================================================================
    const session = await auth(); // 获取当前 Session

    if (!session) {
      return NextResponse.json(
        { success: false, error: '未登录' },
        { status: 401 } // 401 Unauthorized（未授权）
      );
    }

    // ========================================================================
    // 2. 查询用户资料（含统计数据）
    // ========================================================================
    const user = await prisma.user.findUnique({
      where: { id: session.user.id },
      select: {
        id: true,
        email: true,
        name: true,
        avatarUrl: true,
        role: true,
        createdAt: true,
        updatedAt: true,
        _count: {
          // 统计关联数据
          select: {
            conversations: true, // 会话总数
            messages: true, // 消息总数
          },
        },
      },
    });

    // ========================================================================
    // 3. 检查用户是否存在
    // ========================================================================
    if (!user) {
      return NextResponse.json(
        { success: false, error: '用户不存在' },
        { status: 404 } // 404 Not Found
      );
    }

    // ========================================================================
    // 4. 返回用户资料
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: user,
    });
  } catch (error) {
    console.error('获取用户资料失败:', error);
    return NextResponse.json(
      { success: false, error: '获取用户资料失败' },
      { status: 500 } // 500 Internal Server Error
    );
  }
}

/**
 * PATCH - 更新用户个人资料
 *
 * 请求体：
 *   {
 *     name: string,       // 用户名（必填，1-50字符）
 *     avatarUrl?: string  // 头像 URL（可选）
 *   }
 *
 * 功能：
 *   - 验证用户名格式
 *   - 更新用户名和头像
 *   - 返回更新后的用户信息
 *
 * 响应：
 *   {
 *     success: true,
 *     message: '个人资料更新成功',
 *     data: { id, email, name, avatarUrl, role, updatedAt }
 *   }
 */
export async function PATCH(req) {
  try {
    // ========================================================================
    // 1. 验证用户登录状态
    // ========================================================================
    const session = await auth();

    if (!session) {
      return NextResponse.json(
        { success: false, error: '未登录' },
        { status: 401 }
      );
    }

    // ========================================================================
    // 2. 解析请求体
    // ========================================================================
    const { name, avatarUrl } = await req.json();

    // ========================================================================
    // 3. 验证用户名（必填）
    // ========================================================================
    if (!name || name.trim().length === 0) {
      return NextResponse.json(
        { success: false, error: '用户名不能为空' },
        { status: 400 } // 400 Bad Request
      );
    }

    // 验证用户名长度
    if (name.length > 50) {
      return NextResponse.json(
        { success: false, error: '用户名长度不能超过 50 个字符' },
        { status: 400 }
      );
    }

    // ========================================================================
    // 4. 更新用户资料
    // ========================================================================
    const updatedUser = await prisma.user.update({
      where: { id: session.user.id },
      data: {
        name: name.trim(), // 去除首尾空格
        ...(avatarUrl && { avatarUrl }), // 如果提供了头像 URL，则更新
        updatedAt: new Date(), // 更新时间戳
      },
      select: {
        // 只返回需要的字段
        id: true,
        email: true,
        name: true,
        avatarUrl: true,
        role: true,
        updatedAt: true,
      },
    });

    // ========================================================================
    // 5. 返回更新后的用户信息
    // ========================================================================
    return NextResponse.json({
      success: true,
      message: '个人资料更新成功',
      data: updatedUser,
    });
  } catch (error) {
    console.error('更新用户资料失败:', error);
    return NextResponse.json(
      { success: false, error: '更新用户资料失败' },
      { status: 500 }
    );
  }
}
