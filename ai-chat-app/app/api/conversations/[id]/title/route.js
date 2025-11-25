/**
 * ============================================================================
 * 自动生成会话标题 API (app/api/conversations/[id]/title/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   根据会话的前几轮对话内容，使用 AI 自动生成简洁的标题
 *
 * 主要功能：
 *   1. 获取会话的前 3 轮对话（6 条消息）
 *   2. 构建对话摘要
 *   3. 调用 LLM Service 生成标题 ✨ 修改
 *   4. 更新会话标题到数据库
 *
 * 路由：POST /api/conversations/{id}/title
 *
 * 权限：
 *   - 需要登录
 *   - 只能操作自己的会话
 *
 * 使用场景：
 *   - 用户发送第一条消息后自动触发
 *   - 用户手动点击"重新生成标题"按钮
 *
 * AI 模型：
 *   - 使用 gpt-4o-mini（成本低、速度快）
 *   - 通过 LLM Service 调用 ✨ 修改
 *
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { auth } from '@/app/api/auth/[...nextauth]/route';
// 🔴 删除：import { ChatOpenAI } from '@langchain/openai';

// ============================================================================
// ✅ 新增：LLM Service 配置
// ============================================================================
const LLM_SERVICE_URL = process.env.LLM_SERVICE_URL || 'http://llm-service:8002';

/**
 * POST - 自动生成会话标题
 *
 * 流程：
 *   1. 验证用户权限
 *   2. 获取会话的前 6 条消息（3 轮对话）
 *   3. 构建对话摘要（每条消息截取前 100 字符）
 *   4. 调用 LLM Service 生成标题（不超过 20 字）✨ 修改
 *   5. 更新数据库中的会话标题
 *
 * 响应：
 *   {
 *     success: true,
 *     data: { title: string }
 *   }
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
        { status: 401 } // 401 Unauthorized
      );
    }

    // ========================================================================
    // 2. 获取动态路由参数（会话 ID）
    // ========================================================================
    // Next.js 15+ 要求：params 是 Promise，需要 await
    const { id: conversationId } = await params;

    // ========================================================================
    // 3. 查询会话及其前 6 条消息
    // ========================================================================
    const conversation = await prisma.conversation.findUnique({
      where: { id: conversationId },
      include: {
        messages: {
          orderBy: { createdAt: 'asc' }, // 按时间升序排列
          take: 6, // 取前 6 条消息（3 轮对话：用户+AI+用户+AI+用户+AI）
        },
      },
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
        { status: 403 } // 403 Forbidden
      );
    }

    // ========================================================================
    // 4. 检查消息数量（至少需要 2 条消息）
    // ========================================================================
    // 如果消息少于 2 条（1 轮对话），不生成标题
    if (conversation.messages.length < 2) {
      return NextResponse.json({
        success: true,
        data: { title: '新对话' }, // 返回默认标题
      });
    }

    // ========================================================================
    // 5. 构建对话摘要
    // ========================================================================
    // 格式：
    //   用户: 你好，我想了解...
    //   AI: 你好！很高兴为你...
    //   用户: 那么具体怎么...
    const messageSummary = conversation.messages
      .map(
        (msg) =>
          `${msg.role === 'user' ? '用户' : 'AI'}: ${msg.content.substring(0, 100)}`
      )
      .join('\n');

    // ========================================================================
    // 6. 构建提示词
    // ========================================================================
    const prompt = `请根据以下对话内容，生成一个简洁的标题（不超过20个字，不要加引号）：

${messageSummary}

标题：`;

    // ========================================================================
    // 🔴 删除：LangChain 配置和调用
    // ========================================================================
    // const llm = new ChatOpenAI({
    //   modelName: 'openai/gpt-4o-mini',
    //   openAIApiKey: process.env.OPENAI_API_KEY,
    //   configuration: {
    //     baseURL: 'https://openrouter.ai/api/v1',
    //   },
    //   temperature: 0.7,
    // });
    // const response = await llm.invoke([{ role: 'user', content: prompt }]);
    // const title = response.content.trim();

    // ========================================================================
    // ✅ 新增：调用 LLM Service 生成标题
    // ========================================================================
    console.log('📡 调用 LLM Service 生成标题...');

    const llmResponse = await fetch(`${LLM_SERVICE_URL}/api/v1/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
        model: 'openai/gpt-4o-mini', // 使用便宜的模型
        max_tokens: 50, // 标题不需要太长
        temperature: 0.7, // 适中的创造性
      }),
    });

    // 检查 LLM Service 响应
    if (!llmResponse.ok) {
      const errorText = await llmResponse.text();
      console.error('❌ LLM Service 错误:', errorText);

      // 返回默认标题（而不是抛出错误）
      return NextResponse.json({
        success: true,
        data: { title: '新对话' }, // 降级方案
      });
    }

    // 解析响应
    // const llmData = await llmResponse.json();
    // const title = llmData.text.trim(); // 去除首尾空格
    // ========================================================================
    // ✅ 修复：适配 LLM Service 的响应格式
    // ========================================================================

    // 解析响应
    const llmData = await llmResponse.json();
    console.log('📊 LLM Service 响应:', llmData); // 调试日志

    // ✅ 修复：正确提取标题
    let title = '新对话'; // 默认值

    // 优先级 1：标准响应格式 { success: true, data: { response: "..." } }
    if (llmData.success && llmData.data?.response) {
      title = llmData.data.response.trim();
    }
    // 优先级 2：直接在 data 中
    else if (llmData.data?.content) {
      title = llmData.data.content.trim();
    }
    // 优先级 3：直接在根级别
    else if (llmData.content && typeof llmData.content === 'string') {
      title = llmData.content.trim();
    } else if (llmData.text && typeof llmData.text === 'string') {
      title = llmData.text.trim();
    } else if (llmData.response && typeof llmData.response === 'string') {
      title = llmData.response.trim();
    }
    // 优先级 4：纯字符串
    else if (typeof llmData === 'string') {
      title = llmData.trim();
    } else {
      console.warn('⚠️ LLM Service 响应格式未知，使用默认标题');
    }

    // 限制标题长度（最多 50 字符）
    if (title.length > 50) {
      title = title.substring(0, 50) + '...';
    }

    // 移除可能的引号
    title = title.replace(/^["']|["']$/g, '');

    console.log('✅ 生成标题成功:', title);

    // ========================================================================
    // 8. 更新会话标题到数据库
    // ========================================================================
    const updatedConversation = await prisma.conversation.update({
      where: { id: conversationId },
      data: { title },
    });

    // ========================================================================
    // 9. 返回生成的标题
    // ========================================================================
    return NextResponse.json({
      success: true,
      data: { title: updatedConversation.title },
    });
  } catch (error) {
    console.error('❌ 生成标题失败:', error);

    // 返回默认标题（而不是 500 错误）
    return NextResponse.json({
      success: true,
      data: { title: '新对话' }, // 降级方案
    });
  }
}
