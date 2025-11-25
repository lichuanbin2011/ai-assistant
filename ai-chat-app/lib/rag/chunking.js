/**
 * ============================================================================
 * 文本分块工具 (lib/rag/chunking.js)
 * ============================================================================
 *
 * 功能：
 *   1. 递归字符分割
 *   2. 保持语义完整
 *   3. 添加元数据
 *
 * 使用：
 *   import { chunkText } from '@/lib/rag/chunking';
 * ============================================================================
 */

import { RecursiveCharacterTextSplitter } from '@langchain/textsplitters';
import { countTokens } from './embeddings';
import log from '@/lib/log';
// ============================================================================
// 配置
// ============================================================================
const DEFAULT_CHUNK_SIZE = parseInt(process.env.CHUNK_SIZE || '1000');
const DEFAULT_CHUNK_OVERLAP = parseInt(process.env.CHUNK_OVERLAP || '200');

// ============================================================================
// 创建分块器
// ============================================================================
/**
 * 创建文本分块器
 * @param {Object} options - 配置选项
 * @returns {RecursiveCharacterTextSplitter}
 */
export function createSplitter(options = {}) {
  const {
    chunkSize = DEFAULT_CHUNK_SIZE,
    chunkOverlap = DEFAULT_CHUNK_OVERLAP,
    separators = ['\n\n', '\n', '。', '！', '？', '；', '，', ' ', ''],
  } = options;

  return new RecursiveCharacterTextSplitter({
    chunkSize,
    chunkOverlap,
    separators,
    lengthFunction: (text) => text.length, // 按字符计数
  });
}

// ============================================================================
// 文本分块（核心函数）
// ============================================================================
/**
 * 将文本分块
 * @param {string} text - 输入文本
 * @param {Object} metadata - 元数据
 * @param {Object} options - 配置选项
 * @returns {Promise<Array>} 分块结果
 */
export async function chunkText(text, metadata = {}, options = {}) {
  if (!text || !text.trim()) {
    console.warn('log.debug 输入文本为空');
    return [];
  }

  log.debug('log.debug 开始文本分块...');
  log.debug('log.debug 原始文本长度:', text.length);

  const startTime = Date.now();

  try {
    // 创建分块器
    const splitter = createSplitter(options);

    // 执行分块
    const docs = await splitter.createDocuments([text], [metadata]);

    // 处理结果
    const chunks = docs.map((doc, index) => {
      const content = doc.pageContent;
      const tokens = countTokens(content);

      return {
        chunkIndex: index,
        content: content,
        tokenCount: tokens,
        charCount: content.length,
        metadata: {
          ...doc.metadata,
          ...metadata,
        },
      };
    });

    const duration = Date.now() - startTime;

    log.debug('log.debug 分块完成');
    log.debug('log.debug 统计信息:', {
      totalChunks: chunks.length,
      avgChunkSize: Math.round(text.length / chunks.length),
      totalTokens: chunks.reduce((sum, c) => sum + c.tokenCount, 0),
      duration: `${duration}ms`,
    });

    return chunks;
  } catch (error) {
    console.error('log.debug 分块失败:', error);
    throw new Error(`文本分块失败: ${error.message}`);
  }
}

// ============================================================================
// 智能分块（按页码）
// ============================================================================
/**
 * 按页码分块（适合 PDF）
 * @param {Object} pdfData - PDF 解析数据
 * @param {Object} options - 配置选项
 * @returns {Promise<Array>} 分块结果
 */
export async function chunkByPages(pdfData, options = {}) {
  const { text, numpages, metadata } = pdfData;

  log.debug('📄 按页码分块，总页数:', numpages);

  // 如果有页码信息，按页分块
  if (metadata?.pageTexts && Array.isArray(metadata.pageTexts)) {
    const allChunks = [];

    for (const page of metadata.pageTexts) {
      const pageChunks = await chunkText(
        page.text,
        {
          pageNumber: page.page,
          source: 'pdf',
        },
        options
      );

      allChunks.push(...pageChunks);
    }

    return allChunks;
  }

  // 否则整体分块
  return chunkText(text, { source: 'pdf', totalPages: numpages }, options);
}

// ============================================================================
// 导出
// ============================================================================
export default {
  chunkText,
  chunkByPages,
  createSplitter,
};
