/**
 * ============================================================================
 * 会话列表 API (app/api/conversations/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   处理用户的会话列表获取和新会话创建
 *
 * 主要功能：
 *   1. GET：获取当前用户的所有会话（支持分页和搜索）
 *   2. POST：创建新会话
 *
 * 路由：
 *   - GET /api/conversations?page=1&limit=20&search=关键词
 *   - POST /api/conversations
 *
 * 权限：
 *   - 需要登录
 *   - 只能访问自己的会话
 *
 * 分页方式：
 *   - 偏移分页（Offset-based Pagination）
 *   - 适合会话列表（需要跳页功能）
 *
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { auth } from '@/app/api/auth/[...nextauth]/route';

/**
 * GET - 获取用户的所有会话
 *
 * 功能：
 *   - 获取当前用户的会话列表
 *   - 支持分页（page + limit）
 *   - 支持搜索（按标题模糊匹配）
 *   - 按更新时间倒序排列
 *   - 包含每个会话的消息数量
 *
 * 查询参数：
 *   - page: number（默认 1）       // 页码
 *   - limit: number（默认 20）     // 每页数量
 *   - search: string（可选）       // 搜索关键词
 *
 * 响应：
 *   {
 *     success: true,
 *     data: {
 *       conversations: Array<Conversation>,  // 会话列表
 *       pagination: {
 *         page: number,         // 当前页码
 *         limit: number,        // 每页数量
 *         total: number,        // 总记录数
 *         totalPages: number    // 总页数
 *       }
 *     }
 *   }
 */
export async function GET(req) {
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
    // 2. 解析查询参数
    // ========================================================================
    const { searchParams } = new URL(req.url);
    const userId = session.user.id;
    const page = parseInt(searchParams.get('page') || '1'); // 页码（默认 1）
    const limit = parseInt(searchParams.get('limit') || '20'); // 每页数量（默认 20）
    const search = searchParams.get('search') || ''; // 搜索关键词（可选）

    // 计算跳过的记录数（偏移量）
    const skip = (page - 1) * limit;
    // 例如：page=2, limit=20 → skip=20（跳过前 20 条）

    // ========================================================================
    // 3. 构建查询条件
    // ========================================================================
    const where = {
      userId, // 只查询当前用户的会话
      ...(search && {
        title: {
          contains: search, // 模糊匹配（包含关键词）
          mode: 'insensitive', // 不区分大小写
        },
      }),
    };

    // ========================================================================
    // 4. 并行查询会话列表和总数
    // ========================================================================
    //  使用 Promise.all 并行执行，提高性能
    const [conversations, total] = await Promise.all([
      // 查询会话列表
      prisma.conversation.findMany({
        where,
        orderBy: { updatedAt: 'desc' }, // 按更新时间倒序排列
        skip, // 跳过前 N 条记录
        take: limit, // 取 N 条记录
        include: {
          _count: {
            select: { messages: true }, // 统计每个会话的消息数量
          },
        },
      }),
      // 查询总记录数
      prisma.conversation.count({ where }),
    ]);

    // ========================================================================
    // 5. 格式化响应数据
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: {
        // 会话列表（格式化字段）
        conversations: conversations.map((conv) => ({
          id: conv.id,
          title: conv.title,
          model: conv.model,
          createdAt: conv.createdAt,
          updatedAt: conv.updatedAt,
          messageCount: conv._count.messages, // 消息数量
        })),
        // 分页信息
        pagination: {
          page, // 当前页码
          limit, // 每页数量
          total, // 总记录数
          totalPages: Math.ceil(total / limit), // 总页数（向上取整）
        },
      },
    });
  } catch (error) {
    console.error('获取会话列表失败:', error);
    return NextResponse.json(
      { success: false, error: '获取会话列表失败' },
      { status: 500 } // 500 Internal Server Error
    );
  }
}

/**
 * POST - 创建新会话
 *
 * 功能：
 *   - 为当前用户创建一个新的会话
 *   - 设置默认标题和模型
 *
 * 请求体：
 *   {
 *     title?: string,   // 会话标题（可选，默认"新对话"）
 *     model?: string    // AI 模型（可选，默认"gpt-4o"）
 *   }
 *
 * 响应：
 *   {
 *     success: true,
 *     data: {
 *       id: string,
 *       userId: string,
 *       title: string,
 *       model: string,
 *       createdAt: Date,
 *       updatedAt: Date
 *     }
 *   }
 *
 * 使用场景：
 *   - 用户点击"新建对话"按钮
 *   - 用户发送第一条消息时自动创建
 */
export async function POST(req) {
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
    const { title, model } = await req.json();
    const userId = session.user.id;

    // ========================================================================
    // 3. 创建新会话
    // ========================================================================
    const conversation = await prisma.conversation.create({
      data: {
        userId,
        title: title || '新对话', // 默认标题
        model: model || 'gpt-4o', // 默认模型
      },
    });

    // ========================================================================
    // 4. 返回创建的会话
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: conversation,
    });
  } catch (error) {
    console.error('创建会话失败:', error);
    return NextResponse.json(
      { success: false, error: '创建会话失败' },
      { status: 500 }
    );
  }
}
