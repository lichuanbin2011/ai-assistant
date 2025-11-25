/**
 * ============================================================================
 * AI 聊天 API (app/api/chat/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   处理 AI 聊天请求，支持文本、图片输入和联网搜索，返回流式响应
 *
 * 主要功能：
 *   1. 接收用户消息和图片
 *   2. 将本地图片转换为 Base64 格式
 *   3. 调用 LLM Service（支持普通对话和联网搜索）✨ 修改
 *   4. 返回流式响应（Server-Sent Events）
 *
 * 路由：POST /api/chat
 *
 * 请求体：
 *   {
 *     messages: Array<{role, content}>,  // 聊天历史
 *     model: string,                     // 模型名称
 *     images?: Array<string>,            // 图片 URL 列表（可选）
 *     useWebSearch?: boolean             // 🆕 是否使用联网搜索（可选）
 *   }
 *
 * 响应：
 *   - Content-Type: text/event-stream（流式响应）
 *   - 格式：data: {"content": "..."}\n\n
 *
 * 技术栈：
 *   - LLM Service（独立 AI 服务）
 *   - OpenAI API（通过 LLM Service）
 *   - Server-Sent Events（流式传输）
 *
 * ============================================================================
 */

import { promises as fs } from 'fs';
import path from 'path';
import log from '@/lib/log';

// ============================================================================
// LLM Service 配置
// ============================================================================
const LLM_SERVICE_URL = process.env.LLM_SERVICE_URL || 'http://llm-service:8002';

/**
 * POST - AI 聊天接口
 *
 * 流程：
 *   1. 验证请求参数
 *   2. 判断使用普通对话还是联网搜索 🆕
 *   3. 处理图片（转 Base64）
 *   4. 构造多模态消息
 *   5. 调用 LLM Service
 *   6. 返回流式响应
 */
export async function POST(req) {
  try {
    // ========================================================================
    // 1. 解析请求体
    // ========================================================================
    // 🆕 修改：添加 useWebSearch 参数
    const { messages, model, images, useWebSearch = false } = await req.json();

    // 验证必填参数
    if (!messages || !model) {
      return new Response(
        JSON.stringify({
          error: 'Invalid input: messages or model is missing',
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // ========================================================================
    // 🆕 2. 判断使用哪种模式
    // ========================================================================
    const lastMessage = messages[messages.length - 1];
    const userQuery = lastMessage.content;

    // 如果启用联网搜索且没有图片，使用搜索接口
    if (useWebSearch && (!images || images.length === 0)) {
      log.debug('🔍 使用联网搜索模式');
      return handleWebSearch(messages, model, userQuery);
    }

    // 否则使用普通生成接口（支持图片）
    log.debug('💬 使用普通对话模式');
    return handleNormalChat(messages, model, images);
    
  } catch (error) {
    console.error('❌ Error in /api/chat route:', error);

    return new Response(
      JSON.stringify({
        error: 'Internal Server Error',
        details: error.message,
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

// ============================================================================
// 🆕 新增函数：处理普通对话（支持图片）
// ============================================================================
/**
 * 处理普通对话（支持图片）
 * 
 * 这是将原来 POST 函数中的主要逻辑提取出来的函数
 */
async function handleNormalChat(messages, model, images) {
  try {
    // ========================================================================
    // 1. 处理图片输入（转换为 Base64）
    // ✅ 保持不变（从原代码复制）
    // ========================================================================
    const lastMessage = messages[messages.length - 1];
    let processedMessages = [...messages.slice(0, -1)];

    if (images && images.length > 0) {
      try {
        const base64Images = await Promise.all(
          images.map(async (imageUrl) => {
            try {
              if (
                imageUrl.startsWith('http:') ||
                imageUrl.startsWith('/') ||
                imageUrl.startsWith('https:')
              ) {
                let filePath;
                let urlPath;

                if (
                  imageUrl.startsWith('http:') ||
                  imageUrl.startsWith('https:')
                ) {
                  urlPath = new URL(imageUrl).pathname;
                } else {
                  urlPath = imageUrl;
                }

                if (urlPath.includes('/api/files/')) {
                  const actualPath = urlPath.split('/api/files/')[1];
                  filePath = path.join(process.cwd(), 'public', actualPath);
                } else {
                  filePath = path.join(process.cwd(), 'public', urlPath);
                }

                log.debug('🔍 原始 URL:', imageUrl);
                log.debug('🔍 提取路径:', urlPath);
                log.debug('🖼️ 文件路径:', filePath);

                try {
                  await fs.access(filePath);
                } catch {
                  throw new Error(`File not found: ${filePath}`);
                }

                const imageBuffer = await fs.readFile(filePath);
                const base64Image = imageBuffer.toString('base64');

                const ext = path.extname(filePath).toLowerCase();
                let mimeType = 'image/jpeg';
                if (ext === '.png') mimeType = 'image/png';
                else if (ext === '.gif') mimeType = 'image/gif';
                else if (ext === '.webp') mimeType = 'image/webp';

                return `data:${mimeType};base64,${base64Image}`;
              } else {
                return imageUrl;
              }
            } catch (error) {
              console.error(`Error processing image ${imageUrl}:`, error);
              throw error;
            }
          })
        );

        const multimodalMessage = {
          role: 'user',
          content: [
            {
              type: 'text',
              text: lastMessage.content || '请分析这张图片',
            },
            ...base64Images.map((base64Image) => ({
              type: 'image_url',
              image_url: {
                url: base64Image,
              },
            })),
          ],
        };

        processedMessages.push(multimodalMessage);
      } catch (imageError) {
        console.error('Error processing images:', imageError);

        const fallbackMessage = {
          role: 'user',
          content: `${lastMessage.content} [图片处理失败，但用户上传了图片]`,
        };
        processedMessages.push(fallbackMessage);
      }
    } else {
      processedMessages.push(lastMessage);
    }

    // ========================================================================
    // 2. 添加系统提示词（定义 AI 行为）
    // ✅ 保持不变（从原代码复制）
    // ========================================================================
    const systemMessage = {
      role: 'system',
      content: `你是一个专业、友好、博学的 AI 助手，名字可以叫"智能助手"。
                ## 核心能力
                - 💬 自然对话：理解上下文，提供连贯的多轮对话
                - 🧠 知识广博：涵盖技术、科学、人文、生活等多个领域
                - 🎨 创意思维：帮助用户头脑风暴、创作内容
                - 📊 数据分析：解读数据、提供洞察
                - 🖼️ 图像理解：分析和描述图片内容

                ## 回答原则
                1. **结构清晰**：使用标题、列表、表格等 Markdown 格式
                2. **详细全面**：提供完整的背景、步骤、示例
                3. **实用可行**：给出具体可操作的建议
                4. **引用来源**：重要信息标注来源或依据
                5. **友好亲和**：使用适当的表情符号，语气温和

                ## 特殊场景处理
                - **技术问题**：提供代码示例、最佳实践、常见陷阱
                - **学习问题**：给出学习路径、资源推荐、时间规划
                - **创作需求**：激发灵感、提供多个方案
                - **问题诊断**：逐步分析、定位根因、给出解决方案

                ## 回答格式
                - 使用 Markdown 语法美化排版
                - 代码用 \`\`\` 代码块包裹并标注语言
                - 重要内容用 **加粗** 或 > 引用块强调
                - 适当使用表情符号增加可读性（但不过度）

                ## 限制与边界
                - 不提供医疗诊断、法律咨询等专业建议
                - 不生成有害、违法、歧视性内容
                - 遇到不确定的信息会明确说明
                - 不假装能访问实时信息或外部系统
                ## 处理文本和图片
                - 你可以处理文本和图片内容。当用户提供图片时，请详细描述和分析图片内容。`,
    };

    const finalMessages = [systemMessage, ...processedMessages];

    // ========================================================================
    // 3. 调用 LLM Service
    // ✅ 保持不变（从原代码复制）
    // 🆕 修改：添加超时处理
    // ========================================================================
    log.debug('📡 调用 LLM Service:', LLM_SERVICE_URL);
    log.debug('📝 消息数量:', finalMessages.length);
    log.debug('🤖 模型:', model);

    const llmResponse = await fetch(
      `${LLM_SERVICE_URL}/api/v1/generate/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: finalMessages,
          model: model,
          max_tokens: 4000,
          temperature: 0.7,
          stream: true,
        }),
        // 🆕 修改：添加超时（60秒）
        signal: AbortSignal.timeout(60000),
      }
    );

    if (!llmResponse.ok) {
      const errorText = await llmResponse.text();
      console.error('❌ LLM Service 错误:', errorText);

      return new Response(
        JSON.stringify({
          error: 'LLM Service 错误',
          details: errorText,
        }),
        {
          status: llmResponse.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    log.debug('✅ LLM Service 响应成功');

    // ========================================================================
    // 4. 返回流式响应
    // 🆕 修改：调用统一的流处理函数
    // ========================================================================
    return createStreamResponse(llmResponse, false);
    
  } catch (error) {
    console.error('❌ Normal chat error:', error);
    return new Response(
      JSON.stringify({ error: error.message || 'Internal server error' }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// ============================================================================
// 🆕 新增函数：处理联网搜索
// ============================================================================
/**
 * 处理联网搜索
 * 
 * @param {Array} messages - 聊天历史
 * @param {string} model - 模型名称
 * @param {string} userQuery - 用户查询
 */
async function handleWebSearch(messages, model, userQuery) {
  try {
    log.debug('🔍 开始联网搜索:', userQuery);

    // ========================================================================
    // 1. 构建聊天历史（排除最后一条用户消息）
    // ========================================================================
    const chatHistory = messages.slice(0, -1).map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

    // ========================================================================
    // 2. 调用 LLM Service 搜索接口
    // ========================================================================
    const llmResponse = await fetch(
      `${LLM_SERVICE_URL}/api/v1/search/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userQuery,
          model: model,
          chat_history: chatHistory,
          stream: true,
          max_results: 10,
          max_tokens: 4000,
          temperature: 0.7,
        }),
        // 搜索可能更慢，设置 90 秒超时
        signal: AbortSignal.timeout(90000),
      }
    );

    if (!llmResponse.ok) {
      const errorText = await llmResponse.text();
      console.error('❌ LLM Service 搜索错误:', errorText);

      return new Response(
        JSON.stringify({
          error: 'LLM Service 搜索错误',
          details: errorText,
        }),
        {
          status: llmResponse.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    log.debug('✅ LLM Service 搜索响应成功');

    // ========================================================================
    // 3. 返回流式响应（支持搜索结果）
    // ========================================================================
    return createStreamResponse(llmResponse, true); // true 表示搜索模式
    
  } catch (error) {
    console.error('❌ Web search error:', error);
    return new Response(
      JSON.stringify({ error: error.message || 'Search failed' }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// ============================================================================
// 🆕 新增函数：创建流式响应（统一处理）
// ============================================================================
/**
 * 创建流式响应（统一处理普通对话和搜索）
 * 
 * @param {Response} llmResponse - LLM Service 的响应
 * @param {boolean} isSearch - 是否为搜索模式
 */
function createStreamResponse(llmResponse, isSearch = false) {
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const readable = new ReadableStream({
    async start(controller) {
      let isClosed = false;

      // ----------------------------------------------------------------
      // 辅助函数：安全写入数据
      // ✅ 保持不变（从原代码复制）
      // ----------------------------------------------------------------
      const safeEnqueue = (data) => {
        if (isClosed) return false;
        try {
          controller.enqueue(data);
          return true;
        } catch (error) {
          if (error.code === 'ERR_INVALID_STATE') {
            isClosed = true;
            log.debug('Stream closed during enqueue');
            return false;
          }
          throw error;
        }
      };

      // ----------------------------------------------------------------
      // 辅助函数：安全关闭流
      // ✅ 保持不变（从原代码复制）
      // ----------------------------------------------------------------
      const safeClose = () => {
        if (isClosed) return;
        try {
          controller.close();
          isClosed = true;
          log.debug('✅ Stream closed successfully');
        } catch (error) {
          if (error.code === 'ERR_INVALID_STATE') {
            isClosed = true;
            log.debug('Stream already closed');
          } else {
            console.error('Error closing stream:', error);
          }
        }
      };

      try {
        // ✅ 保持不变（从原代码复制）
        const reader = llmResponse.body.getReader();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            log.debug('📭 LLM Service 流结束');
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (isClosed) {
              log.debug('Stream closed, stopping iteration');
              break;
            }

            if (!line.trim() || line.startsWith(':')) {
              continue;
            }

            if (line.startsWith('data: ')) {
              const data = line.slice(6);

              if (data === '[DONE]') {
                log.debug('📭 收到 [DONE] 标记');
                break;
              }

              try {
                const json = JSON.parse(data);

                // 🆕 修改：处理不同类型的事件
                if (json.type === 'content' || json.content) {
                  // 内容块（兼容两种格式）
                  const content = json.type === 'content' ? json.content : json.content;
                  const success = safeEnqueue(
                    encoder.encode(
                      `data: ${JSON.stringify({ content })}\n\n`
                    )
                  );

                  if (!success) {
                    log.debug('Client disconnected, stopping stream');
                    break;
                  }
                } 
                // 🆕 新增：处理搜索结果
                else if (json.type === 'search_results' && isSearch) {
                  log.debug('📊 收到搜索结果:', json.results?.length || 0);
                  safeEnqueue(
                    encoder.encode(
                      `data: ${JSON.stringify({ 
                        type: 'search_results', 
                        results: json.results 
                      })}\n\n`
                    )
                  );
                } 
                // 🆕 新增：处理状态消息
                else if (json.type === 'status' && isSearch) {
                  log.debug('ℹ️ 状态:', json.message);
                  safeEnqueue(
                    encoder.encode(
                      `data: ${JSON.stringify({ 
                        type: 'status', 
                        message: json.message 
                      })}\n\n`
                    )
                  );
                } 
                // ✅ 保持不变：处理错误
                else if (json.error || json.type === 'error') {
                  console.error('LLM Service 错误:', json.error || json.message);
                  safeEnqueue(
                    encoder.encode(
                      `data: ${JSON.stringify({ 
                        error: json.error || json.message 
                      })}\n\n`
                    )
                  );
                  break;
                }
              } catch (parseError) {
                log.debug('无法解析的数据:', data);
              }
            }
          }

          if (isClosed) break;
        }

        safeClose();
      } catch (error) {
        console.error('❌ 流式处理错误:', error);
        safeEnqueue(
          encoder.encode(
            `data: ${JSON.stringify({ error: 'Stream error' })}\n\n`
          )
        );
        safeClose();
      }
    },

    // ✅ 保持不变（从原代码复制）
    cancel(reason) {
      log.debug('Stream cancelled by client:', reason);
    },
  });

  // ✅ 保持不变（从原代码复制）
  return new Response(readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  });
}
