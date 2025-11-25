/**
 * ============================================================================
 * 消息操作 API (app/api/messages/[id]/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   处理单个消息的查询、更新和删除操作
 *
 * 主要功能：
 *   1. GET：获取单条消息（ 新增，包含 citations）
 *   2. PATCH：更新消息内容（ 支持更新引用来源和联网搜索标识）
 *   3. DELETE：删除消息
 *
 * 路由：
 *   - GET /api/messages/:id      新增
 *   - PATCH /api/messages/:id
 *   - DELETE /api/messages/:id
 *
 * 权限验证：
 *   - 需要登录
 *   - 只能操作自己会话中的消息（通过 conversation.userId 验证）
 *
 * 修改记录：
 *   - 2025-11-15：添加 GET 方法（获取单条消息）
 *   - 支持获取消息的完整 citations 数据
 *
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { auth } from '@/app/api/auth/[...nextauth]/route';

/**
 * ============================================================================
 * GET - 获取单条消息（ 新增）
 * ============================================================================
 *
 * 功能：
 *   - 获取指定消息的完整信息
 *   - 包含引用来源（citations）
 *   - 验证用户权限
 *
 * 使用场景：
 *   1. 流式输出完成后，刷新消息以获取完整的 citations
 *   2. 前端需要重新加载单条消息的详细信息
 *   3. 确保 citations 数据完整性
 *
 * 路由参数：
 *   - id: string  // 消息 ID（从 URL 路径获取）
 *
 * 响应：
 *   {
 *     success: true,
 *     data: {
 *       id: string,
 *       conversationId: string,
 *       role: 'user' | 'assistant',
 *       content: string,
 *       tokensUsed: number,
 *       isWebSearch: boolean,
 *       citations: Array,        //  引用来源数组
 *       createdAt: Date,
 *       updatedAt: Date
 *     }
 *   }
 *
 * 错误码：
 *   - 401: 未登录
 *   - 403: 无权限访问此消息
 *   - 404: 消息不存在
 *   - 500: 服务器错误
 */
export async function GET(req, { params }) {
  try {
    // ========================================================================
    // 1. 验证用户登录状态
    // ========================================================================
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { success: false, error: '未授权' },
        { status: 401 }
      );
    }

    // ========================================================================
    // 2. 获取路由参数
    // ========================================================================
    const { id: messageId } = await params;

    // ========================================================================
    // 3. 从数据库查询消息（包含关联的会话信息）
    // ========================================================================
    const message = await prisma.message.findUnique({
      where: { id: messageId },
      include: {
        conversation: {
          select: { userId: true }, // 只查询 userId 用于权限验证
        },
      },
    });

    // ========================================================================
    // 4. 验证消息是否存在
    // ========================================================================
    if (!message) {
      return NextResponse.json(
        { success: false, error: '消息不存在' },
        { status: 404 }
      );
    }

    // ========================================================================
    // 5. 验证用户权限（防止越权访问）
    // ========================================================================
    if (message.conversation.userId !== session.user.id) {
      return NextResponse.json(
        { success: false, error: '无权访问此消息' },
        { status: 403 }
      );
    }

    // ========================================================================
    // 6. 返回消息数据（ 包含 citations）
    // ========================================================================
    const responseData = {
      id: message.id,
      conversationId: message.conversationId,
      role: message.role,
      content: message.content,
      tokensUsed: message.tokensUsed || 0,
      isWebSearch: message.isWebSearch || false,
      citations: message.citations || [], //  引用来源
      createdAt: message.createdAt,
      updatedAt: message.updatedAt,
    };

    //  调试日志（仅开发环境）
    if (process.env.NODE_ENV === 'development') {
      console.log(` GET /api/messages/${messageId}:`, {
        role: responseData.role,
        isWebSearch: responseData.isWebSearch,
        citationsCount: responseData.citations?.length || 0,
      });
    }

    return NextResponse.json({
      success: true,
      data: responseData,
    });
  } catch (error) {
    console.error(' 获取消息失败:', error);
    return NextResponse.json(
      { success: false, error: '获取消息失败' },
      { status: 500 }
    );
  }
}

/**
 * ============================================================================
 * PATCH - 更新消息内容
 * ============================================================================
 *
 * 功能：
 *   - 更新指定消息的内容和 token 使用量
 *   -  支持：更新引用来源（citations）
 *   -  支持：更新联网搜索标识（isWebSearch）
 *   - 主要用于 AI 流式输出完成后，保存完整的回复内容
 *
 * 使用场景：
 *   1. AI 流式输出时，前端实时显示部分内容
 *   2. 流式输出完成后，调用此接口保存完整内容到数据库
 *   3. 更新 token 使用量（用于计费统计）
 *   4.  保存联网搜索的引用来源
 *
 * 路由参数：
 *   - id: string  // 消息 ID（从 URL 路径获取）
 *
 * 请求体：
 *   {
 *     content: string,           // 完整的消息内容
 *     tokensUsed?: number,       // token 使用量（可选）
 *     citations?: Array,         //  引用来源数组（可选）
 *     isWebSearch?: boolean      //  是否为联网搜索（可选）
 *   }
 *
 * 响应：
 *   {
 *     success: true,
 *     data: {
 *       id: string,
 *       conversationId: string,
 *       role: 'user' | 'assistant',
 *       content: string,
 *       tokensUsed: number,
 *       citations: Array,        //  引用来源
 *       isWebSearch: boolean,    //  联网搜索标识
 *       createdAt: Date
 *     }
 *   }
 *
 * 错误码：
 *   - 401: 未登录
 *   - 403: 无权限操作此消息
 *   - 404: 消息不存在
 *   - 500: 服务器错误
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
        { status: 401 }
      );
    }

    // ========================================================================
    // 2. 获取路由参数和请求体
    // ========================================================================
    const { id: messageId } = await params;

    //  解构新增的字段
    const {
      content,
      tokensUsed,
      citations, //  引用来源
      isWebSearch, //  联网搜索标识
    } = await req.json();

    // ========================================================================
    // 3. 查询消息并验证所有权
    // ========================================================================
    const message = await prisma.message.findUnique({
      where: { id: messageId },
      include: {
        conversation: true,
      },
    });

    // ========================================================================
    // 4. 验证消息是否存在
    // ========================================================================
    if (!message) {
      return NextResponse.json(
        { success: false, error: '消息不存在' },
        { status: 404 }
      );
    }

    // ========================================================================
    // 5. 验证用户权限（防止越权访问）
    // ========================================================================
    if (message.conversation.userId !== session.user.id) {
      return NextResponse.json(
        { success: false, error: '无权限操作此消息' },
        { status: 403 }
      );
    }

    // ========================================================================
    // 6. 更新消息内容（ 包含新字段）
    // ========================================================================
    const updatedMessage = await prisma.message.update({
      where: { id: messageId },
      data: {
        content,
        // 条件更新：只有传入时才更新
        ...(tokensUsed !== undefined && { tokensUsed }),
        //  条件更新引用来源
        ...(citations !== undefined && { citations }),
        //  条件更新联网搜索标识
        ...(isWebSearch !== undefined && { isWebSearch }),
      },
    });

    //  日志记录（仅开发环境）
    if (process.env.NODE_ENV === 'development') {
      console.log(` PATCH /api/messages/${messageId}:`, {
        contentLength: content?.length,
        citationsCount: citations?.length || 0,
        isWebSearch: isWebSearch || false,
      });
    }

    // ========================================================================
    // 7. 返回更新后的消息
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: updatedMessage,
    });
  } catch (error) {
    console.error(' 更新消息失败:', error);
    return NextResponse.json(
      { success: false, error: '更新消息失败' },
      { status: 500 }
    );
  }
}

/**
 * ============================================================================
 * DELETE - 删除消息
 * ============================================================================
 *
 * 功能：
 *   - 删除指定的消息
 *   - 验证用户权限（只能删除自己会话中的消息）
 *   -  自动删除关联的引用来源数据（如果 citations 是关联表）
 *
 * 使用场景：
 *   - 用户想删除某条错误的消息
 *   - 清理会话历史
 *   - 撤回刚发送的消息
 *
 * 路由参数：
 *   - id: string  // 消息 ID
 *
 * 响应：
 *   {
 *     success: true,
 *     message: '消息已删除'
 *   }
 *
 * 错误码：
 *   - 401: 未登录
 *   - 403: 无权限操作此消息
 *   - 404: 消息不存在
 *   - 500: 服务器错误
 *
 * ⚠️ 注意事项：
 *   - 删除消息会同时删除关联的引用来源（citations 字段）
 *   - 删除消息不会删除关联的会话
 *   - 如果删除所有消息，会话仍然存在（变为空会话）
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
    // 2. 获取路由参数
    // ========================================================================
    const { id: messageId } = await params;

    // ========================================================================
    // 3. 查询消息并验证所有权
    // ========================================================================
    const message = await prisma.message.findUnique({
      where: { id: messageId },
      include: {
        conversation: true,
      },
    });

    // ========================================================================
    // 4. 验证消息是否存在
    // ========================================================================
    if (!message) {
      return NextResponse.json(
        { success: false, error: '消息不存在' },
        { status: 404 }
      );
    }

    // ========================================================================
    // 5. 验证用户权限
    // ========================================================================
    if (message.conversation.userId !== session.user.id) {
      return NextResponse.json(
        { success: false, error: '无权限操作此消息' },
        { status: 403 }
      );
    }

    //  删除前记录日志（仅开发环境）
    if (process.env.NODE_ENV === 'development') {
      const citationsCount = message.citations?.length || 0;
      if (citationsCount > 0) {
        console.log(
          `⚠️ DELETE /api/messages/${messageId}: 包含 ${citationsCount} 个引用来源`
        );
      }
    }

    // ========================================================================
    // 6. 删除消息（ 自动删除关联的 citations 数据）
    // ========================================================================
    await prisma.message.delete({
      where: { id: messageId },
    });

    //  日志记录（仅开发环境）
    if (process.env.NODE_ENV === 'development') {
      console.log(` DELETE /api/messages/${messageId}: 消息已删除`);
    }

    // ========================================================================
    // 7. 返回成功响应
    // ========================================================================
    return NextResponse.json({
      success: true,
      message: '消息已删除',
    });
  } catch (error) {
    console.error(' 删除消息失败:', error);
    return NextResponse.json(
      { success: false, error: '删除消息失败' },
      { status: 500 }
    );
  }
}
