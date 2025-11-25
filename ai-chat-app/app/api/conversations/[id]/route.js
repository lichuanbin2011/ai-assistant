/**
 * ============================================================================
 * 单个会话操作 API (app/api/conversations/[id]/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   处理单个会话的更新和删除操作
 *
 * 主要功能：
 *   1. PATCH：更新会话（重命名、切换模型）
 *   2. DELETE：删除会话（级联删除消息）
 *
 * 路由：
 *   - PATCH /api/conversations/{id}
 *   - DELETE /api/conversations/{id}
 *
 * 权限：
 *   - 需要登录
 *   - 只能操作自己的会话
 *
 * 动态路由参数：
 *   - [id]：会话 ID（从 URL 中提取）
 *
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { auth } from '@/app/api/auth/[...nextauth]/route'; // NextAuth 认证函数

/**
 * PATCH - 更新会话
 *
 * 功能：
 *   - 重命名会话标题
 *   - 切换 AI 模型
 *
 * 请求体：
 *   {
 *     title?: string,   // 新标题（可选）
 *     model?: string    // 新模型（可选）
 *   }
 *
 * 响应：
 *   {
 *     success: true,
 *     data: { id, title, model, updatedAt, ... }
 *   }
 *
 * 权限验证：
 *   - 检查用户登录状态
 *   - 验证会话所有权（userId）
 */
export async function PATCH(req, { params }) {
  try {
    // ========================================================================
    // 1. 验证用户登录状态
    // ========================================================================
    const session = await auth();
    if (!session) {
      return NextResponse.json(
        { success: false, error: '未登录' },
        { status: 401 } // 401 Unauthorized
      );
    }

    // ========================================================================
    // 2. 获取动态路由参数（会话 ID）
    // ========================================================================
    //  Next.js 15+ 要求：params 是 Promise，需要 await
    const { id: conversationId } = await params;

    // 解析请求体
    const { title, model } = await req.json();

    // ========================================================================
    // 3. 验证会话所有权
    // ========================================================================
    const conversation = await prisma.conversation.findUnique({
      where: { id: conversationId },
    });

    // 检查会话是否存在
    if (!conversation) {
      return NextResponse.json(
        { success: false, error: '会话不存在' },
        { status: 404 } // 404 Not Found
      );
    }

    // 检查是否为会话所有者
    if (conversation.userId !== session.user.id) {
      return NextResponse.json(
        { success: false, error: '无权限操作此会话' },
        { status: 403 } // 403 Forbidden（禁止访问）
      );
    }

    // ========================================================================
    // 4. 更新会话数据
    // ========================================================================
    const updatedConversation = await prisma.conversation.update({
      where: { id: conversationId },
      data: {
        ...(title && { title }), // 如果提供了 title，则更新
        ...(model && { model }), // 如果提供了 model，则更新
        updatedAt: new Date(), // 更新时间戳
      },
    });

    // ========================================================================
    // 5. 返回更新后的会话数据
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: updatedConversation,
    });
  } catch (error) {
    console.error('更新会话失败:', error);
    return NextResponse.json(
      { success: false, error: '更新会话失败' },
      { status: 500 } // 500 Internal Server Error
    );
  }
}

/**
 * DELETE - 删除会话
 *
 * 功能：
 *   - 删除会话记录
 *   - 级联删除相关消息（通过 Prisma Schema 配置）
 *
 * 响应：
 *   {
 *     success: true,
 *     message: '会话已删除'
 *   }
 *
 * 权限验证：
 *   - 检查用户登录状态
 *   - 验证会话所有权（userId）
 *
 * 级联删除：
 *   - Conversation 删除后，相关 Message 会自动删除
 *   - 在 Prisma Schema 中配置：onDelete: Cascade
 */
export async function DELETE(req, { params }) {
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
    // 2. 获取动态路由参数（会话 ID）
    // ========================================================================
    //  Next.js 15+ 要求：params 是 Promise，需要 await
    const { id: conversationId } = await params;

    // ========================================================================
    // 3. 验证会话所有权
    // ========================================================================
    const conversation = await prisma.conversation.findUnique({
      where: { id: conversationId },
    });

    // 检查会话是否存在
    if (!conversation) {
      return NextResponse.json(
        { success: false, error: '会话不存在' },
        { status: 404 }
      );
    }

    // 检查是否为会话所有者
    if (conversation.userId !== session.user.id) {
      return NextResponse.json(
        { success: false, error: '无权限操作此会话' },
        { status: 403 }
      );
    }

    // ========================================================================
    // 4. 删除会话（级联删除消息）
    // ========================================================================
    //  级联删除：Prisma Schema 中配置了 onDelete: Cascade
    // 删除 Conversation 时，相关的 Message 会自动删除
    await prisma.conversation.delete({
      where: { id: conversationId },
    });

    // ========================================================================
    // 5. 返回成功响应
    // ========================================================================
    return NextResponse.json({
      success: true,
      message: '会话已删除',
    });
  } catch (error) {
    console.error('删除会话失败:', error);
    return NextResponse.json(
      { success: false, error: '删除会话失败' },
      { status: 500 }
    );
  }
}
