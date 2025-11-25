/**
 * ============================================================================
 * Embedding 工具 (lib/rag/embeddings.js)
 * ============================================================================
 *
 * 功能：
 *   1. 文本向量化（单个/批量）
 *   2. Token 计数
 *   3. 成本估算
 *
 * 修改记录：
 *   - 2025-01-XX：集成 Python Embedding Service，保留降级逻辑
 *
 * 使用策略：
 *   - 优先调用 Python Embedding Service（带缓存）
 *   - 服务不可用时降级到 OpenRouter 直连
 *
 * ============================================================================
 */

import { encoding_for_model } from 'tiktoken';
import log from '@/lib/log';

// ============================================================================
// 配置
// ============================================================================
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const OPENAI_BASE_URL =
  process.env.OPENAI_BASE_URL || 'https://openrouter.ai/api/v1';
const EMBEDDING_MODEL = process.env.OPENAI_EMBEDDING_MODEL || 'baai/bge-m3';
const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'AI Chat App';

// ============================================================================
// 🆕 新增：Python Embedding Service 配置
// ============================================================================
const EMBEDDING_SERVICE_URL =
  process.env.EMBEDDING_SERVICE_URL || 'http://llm-service:8002';
const USE_EMBEDDING_SERVICE = process.env.USE_EMBEDDING_SERVICE !== 'false'; // 默认启用

// ============================================================================
// Token 计数器
// ============================================================================
let tokenizer;
try {
  tokenizer = encoding_for_model('gpt-3.5-turbo');
} catch (error) {
  console.warn('Tiktoken 初始化失败，使用估算方法');
}

export function countTokens(text) {
  if (!text) return 0;

  if (tokenizer) {
    try {
      const tokens = tokenizer.encode(text);
      return tokens.length;
    } catch (error) {
      console.error('Token 计数失败:', error);
    }
  }

  return Math.ceil(text.length / 4);
}

// ============================================================================
// 🆕 新增：调用 Python Embedding Service
// ============================================================================
/**
 * 调用 Python Embedding Service 进行向量化
 * @param {string|string[]} texts - 单个文本或文本数组
 * @returns {Promise<Object>} 包含 embeddings 和统计信息
 */
async function callEmbeddingService(texts) {
  try {
    const textsArray = Array.isArray(texts) ? texts : [texts];
    log.debug(`🐍 调用 Python Embedding Service: ${textsArray.length} 个文本`);
    const startTime = Date.now();

    const response = await fetch(`${EMBEDDING_SERVICE_URL}/api/v1/embed`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        texts: textsArray,
        model: EMBEDDING_MODEL,
      }),
      signal: AbortSignal.timeout(60000), // 60 秒超时
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Embedding Service 错误 (${response.status}): ${errorText}`
      );
    }

    const data = await response.json();
    const duration = Date.now() - startTime;

    log.debug(`✅ Python Embedding Service 完成，耗时: ${duration}ms`);
    log.debug(`   - 缓存命中: ${data.cache_stats?.hits || 0}`);
    log.debug(`   - 缓存未命中: ${data.cache_stats?.misses || 0}`);
    log.debug(
      `   - 命中率: ${((data.cache_stats?.hit_rate || 0) * 100).toFixed(1)}%`
    );

    // 提取 embeddings
    const embeddings = data.data.map((item) => item.embedding);

    return {
      embeddings,
      usage: data.usage,
      cache_stats: data.cache_stats,
    };
  } catch (error) {
    console.error('❌ 调用 Python Embedding Service 失败:', error);
    throw error;
  }
}

// ============================================================================
// 🆕 新增：降级逻辑 - 直接调用 OpenRouter API
// ============================================================================
/**
 * 降级方案：直接调用 OpenRouter API
 * @param {string|string[]} texts - 单个文本或文本数组
 * @returns {Promise<Object>} 包含 embeddings 和统计信息
 */
async function callOpenRouterDirectly(texts) {
  log.debug('⚠️ 降级：直接调用 OpenRouter API');

  const textsArray = Array.isArray(texts) ? texts : [texts];

  const response = await fetch(`${OPENAI_BASE_URL}/embeddings`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': APP_URL,
      'X-Title': APP_NAME,
    },
    body: JSON.stringify({
      model: EMBEDDING_MODEL,
      input: textsArray,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`OpenRouter API 错误 (${response.status}): ${errorText}`);
  }

  const data = await response.json();

  // 验证返回格式
  if (!data.data || !Array.isArray(data.data) || data.data.length === 0) {
    throw new Error(`API 返回格式错误: ${JSON.stringify(data)}`);
  }

  const embeddings = data.data.map((item) => item.embedding);

  return {
    embeddings,
    usage: data.usage,
  };
}

// ============================================================================
// 🔄 修改：单个文本向量化（优先使用 Python 服务）
// ============================================================================
export async function embedText(text) {
  if (!text || !text.trim()) {
    throw new Error('文本不能为空');
  }

  if (!OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY 未配置');
  }

  try {
    log.debug('开始向量化，文本长度:', text.length);

    // ========================================================================
    // 🆕 策略1：优先使用 Python Embedding Service
    // ========================================================================
    if (USE_EMBEDDING_SERVICE) {
      try {
        const result = await callEmbeddingService([text]);
        return result.embeddings[0];
      } catch (serviceError) {
        console.warn(
          '⚠️ Python Embedding Service 不可用，降级到直接调用'
        );
        log.debug(`   降级原因: ${serviceError.message}`);
      }
    }

    // ========================================================================
    // 🆕 策略2：降级到直接调用 OpenRouter
    // ========================================================================
    const result = await callOpenRouterDirectly([text]);
    return result.embeddings[0];
  } catch (error) {
    console.error('❌ 向量化失败:', error);
    console.error('配置信息:', {
      baseURL: OPENAI_BASE_URL,
      model: EMBEDDING_MODEL,
      apiKey: OPENAI_API_KEY ? `${OPENAI_API_KEY.slice(0, 10)}...` : '未配置',
      textLength: text.length,
      useEmbeddingService: USE_EMBEDDING_SERVICE, // 🆕 新增日志
      embeddingServiceUrl: EMBEDDING_SERVICE_URL, // 🆕 新增日志
    });
    throw new Error(`向量化失败: ${error.message}`);
  }
}

// ============================================================================
// 🔄 修改：批量文本向量化（优先使用 Python 服务）
// ============================================================================
export async function embedBatch(texts, options = {}) {
  const {
    batchSize = 50, // OpenRouter 建议批次大小
    showProgress = true,
  } = options;

  if (!texts || texts.length === 0) {
    return [];
  }

  if (!OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY 未配置');
  }

  log.debug(`批量向量化开始，总数: ${texts.length}`);
  log.debug(`  - 模型: ${EMBEDDING_MODEL}`);
  // 🆕 修改：添加使用服务的日志
  log.debug(
    `  - 使用服务: ${USE_EMBEDDING_SERVICE ? 'Python Embedding Service' : 'OpenRouter 直连'}`
  );

  const startTime = Date.now();

  try {
    // ========================================================================
    // 🆕 策略1：优先使用 Python Embedding Service
    // ========================================================================
    if (USE_EMBEDDING_SERVICE) {
      try {
        const result = await callEmbeddingService(texts);

        if (showProgress) {
          log.debug(`✅ 批量向量化完成`);
          log.debug(`   - 总数: ${result.embeddings.length}`);
          log.debug(
            `   - 缓存命中率: ${((result.cache_stats?.hit_rate || 0) * 100).toFixed(1)}%`
          );
          log.debug(
            `   - 总 Tokens: ${result.usage?.total_tokens || 'N/A'}`
          );
        }

        return result.embeddings;
      } catch (serviceError) {
        console.warn(
          '⚠️ Python Embedding Service 不可用，降级到直接调用'
        );
        log.debug(`   降级原因: ${serviceError.message}`);
      }
    }

    // ========================================================================
    // 🆕 策略2：降级到直接调用 OpenRouter（分批处理）
    // ========================================================================
    log.debug('⚠️ 使用 OpenRouter 直连（分批处理）');
    const results = [];
    let totalCost = 0;

    // 分批处理
    for (let i = 0; i < texts.length; i += batchSize) {
      const batch = texts.slice(i, i + batchSize);
      const batchNum = Math.floor(i / batchSize) + 1;
      const totalBatches = Math.ceil(texts.length / batchSize);

      if (showProgress) {
        log.debug(
          `处理批次 ${batchNum}/${totalBatches} (${batch.length} 个文本)`
        );
      }

      try {
        // 🔄 修改：使用新的降级函数
        const result = await callOpenRouterDirectly(batch);
        results.push(...result.embeddings);

        // 累计成本
        if (result.usage?.cost) {
          totalCost += parseFloat(result.usage.cost);
        }

        log.debug(`  批次 ${batchNum} 完成`);
      } catch (error) {
        console.error(`❌ 批次 ${batchNum} 失败:`, error.message);

        // 失败时逐个重试
        log.debug(`  逐个重试批次 ${batchNum}...`);
        for (let j = 0; j < batch.length; j++) {
          try {
            const vector = await embedText(batch[j]);
            results.push(vector);

            // 避免频繁请求
            if (j < batch.length - 1) {
              await new Promise((resolve) => setTimeout(resolve, 300));
            }
          } catch (retryError) {
            console.error(
              `  文本 ${i + j} 重试失败:`,
              retryError.message
            );
            // 返回零向量（避免数据库错误）
            results.push(new Array(1024).fill(0));
          }
        }
      }

      // 批次间延迟，避免限流
      if (i + batchSize < texts.length) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }

    const duration = Date.now() - startTime;
    log.debug(`✅ 批量向量化完成（降级模式），耗时: ${duration}ms`);
    log.debug(`   - 总成本: $${totalCost.toFixed(6)}`);

    return results;
  } catch (error) {
    console.error('❌ 批量向量化失败:', error);
    throw new Error(`批量向量化失败: ${error.message}`);
  }
}

// ============================================================================
// 成本估算（保持不变）
// ============================================================================
export function estimateCost(tokenCount) {
  // OpenAI text-embedding-3-small: $0.02 / 1M tokens
  const costPerMillion = 0.00001;
  const cost = (tokenCount / 1000000) * costPerMillion;

  return {
    tokens: tokenCount,
    cost: cost.toFixed(6),
    costUSD: `$${cost.toFixed(6)}`,
    costCNY: `¥${(cost * 7.2).toFixed(4)}`,
  };
}

// ============================================================================
// 导出（保持不变）
// ============================================================================
export default {
  embedText,
  embedBatch,
  countTokens,
  estimateCost,
};
