/**
 * ============================================================================
 * 会话消息 API (app/api/conversations/[id]/messages/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   处理单个会话的消息获取和发送
 *
 * 主要功能：
 *   1. GET：获取会话的所有消息（支持分页）
 *   2. POST：发送新消息（用户消息 + AI 占位符）
 *
 * 路由：
 *   - GET /api/conversations/{id}/messages?limit=50&before=xxx
 *   - POST /api/conversations/{id}/messages
 *
 * 权限：
 *   - 需要登录
 *   - 只能访问自己的会话
 *
 * 动态路由参数：
 *   - [id]：会话 ID（从 URL 中提取）
 *
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { auth } from '@/app/api/auth/[...nextauth]/route';

/**
 * GET - 获取会话的所有消息
 *
 * 功能：
 *   - 获取指定会话的消息列表
 *   - 支持分页加载（游标分页）
 *   - 按时间升序排列
 *
 * 查询参数：
 *   - limit: number（默认 50）  // 每页消息数量
 *   - before: string（可选）    // 游标 ID（用于加载更早的消息）
 *
 * 响应：
 *   {
 *     success: true,
 *     data: {
 *       messages: Array<Message>,  // 消息列表
 *       hasMore: boolean           // 是否还有更多消息
 *     }
 *   }
 *
 * 分页逻辑：
 *   - 使用游标分页（Cursor-based Pagination）
 *   - before：获取 ID 小于此值的消息（更早的消息）
 */
export async function GET(req, { params }) {
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
    // 2. 获取动态路由参数和查询参数
    // ========================================================================
    //  Next.js 15+ 要求：params 是 Promise，需要 await
    const { id: conversationId } = await params;

    // 解析 URL 查询参数
    const { searchParams } = new URL(req.url);
    const limit = parseInt(searchParams.get('limit') || '50'); // 默认 50 条
    const before = searchParams.get('before'); // 游标 ID（可选）

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
        { success: false, error: '无权限访问此会话' },
        { status: 403 } // 403 Forbidden
      );
    }

    // ========================================================================
    // 4. 构造查询条件（支持游标分页）
    // ========================================================================
    const where = {
      conversationId,
      ...(before && {
        id: { lt: before }, // lt = less than（小于），获取更早的消息
      }),
    };

    // ========================================================================
    // 5. 查询消息列表
    // ========================================================================
    const messages = await prisma.message.findMany({
      where,
      orderBy: { createdAt: 'asc' }, // 按创建时间升序排列
      take: limit, // 限制返回数量
    });

    // ========================================================================
    // 6. 返回消息列表和分页信息
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: {
        messages,
        hasMore: messages.length === limit, // 如果返回数量等于 limit，说明可能还有更多
      },
    });
  } catch (error) {
    console.error('获取消息失败:', error);
    return NextResponse.json(
      { success: false, error: '获取消息失败' },
      { status: 500 } // 500 Internal Server Error
    );
  }
}

/**
 * POST - 发送新消息
 *
 * 功能：
 *   1. 保存用户消息到数据库
 *   2. 创建 AI 消息占位符（content 为空）
 *   3. 更新会话的 updatedAt 时间戳
 *
 * 请求体：
 *   {
 *     content: string,       // 消息内容
 *     images?: string[],     // 图片 URL 列表（可选）
 *     model: string          // AI 模型名称
 *   }
 *
 * 响应：
 *   {
 *     success: true,
 *     data: {
 *       userMessage: Message,   // 用户消息对象
 *       aiMessage: Message      // AI 消息占位符
 *     }
 *   }
 *
 * 流程：
 *   1. 验证权限
 *   2. 保存用户消息
 *   3. 创建 AI 消息占位符（content = ''）
 *   4. 更新会话时间
 *   5. 返回两条消息
 *
 *  注意：
 *   - AI 消息的 content 初始为空字符串
 *   - 实际内容由前端通过 /api/chat 接口流式获取后更新
 */
export async function POST(req, { params }) {
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
    // 2. 获取动态路由参数和请求体
    // ========================================================================
    //  Next.js 15+ 要求：params 是 Promise，需要 await
    const { id: conversationId } = await params;
    const { content, images, model } = await req.json();

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
    // 4. 保存用户消息
    // ========================================================================
    const userMessage = await prisma.message.create({
      data: {
        conversationId,
        role: 'user', // 用户消息
        content, // 消息内容
        images: images || [], // 图片列表（默认空数组）
      },
    });

    // ========================================================================
    // 5. 创建 AI 消息占位符
    // ========================================================================
    //  占位符作用：
    //   - 立即返回消息 ID 给前端
    //   - 前端通过 /api/chat 接口流式获取 AI 回复
    //   - 流式接收完成后，前端更新此消息的 content
    const aiMessage = await prisma.message.create({
      data: {
        conversationId,
        role: 'assistant', // AI 消息
        content: '', // 初始为空字符串
        model, // AI 模型名称
      },
    });

    // ========================================================================
    // 6. 更新会话的 updatedAt 时间戳
    // ========================================================================
    await prisma.conversation.update({
      where: { id: conversationId },
      data: { updatedAt: new Date() },
    });

    // ========================================================================
    // 7. 返回用户消息和 AI 占位符
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: {
        userMessage, // 用户消息（完整内容）
        aiMessage, // AI 消息（content 为空）
      },
    });
  } catch (error) {
    console.error('发送消息失败:', error);
    return NextResponse.json(
      { success: false, error: '发送消息失败' },
      { status: 500 }
    );
  }
}
