/**
 * ============================================================================
 * 向量检索工具 (lib/rag/retrieval.js)
 * ============================================================================
 */

import { prisma } from '@/lib/prisma';
import { embedText } from './embeddings';
import { Prisma } from '@prisma/client';
import log from '@/lib/log';

const DEFAULT_TOP_K = parseInt(process.env.RETRIEVAL_TOP_K || '5');
const DEFAULT_THRESHOLD = parseFloat(process.env.SIMILARITY_THRESHOLD || '0.7');

export async function searchSimilarChunks(query, options = {}) {
  const {
    pdfId = null,
    topK = DEFAULT_TOP_K,
    threshold = DEFAULT_THRESHOLD,
    includeMetadata = true,
  } = options;

  try {
    const queryVector = await embedText(query);
    log.debug('查询向量化完成');

    const vectorString = `[${queryVector.join(',')}]`;

    log.debug('执行数据库查询...');
    log.debug('使用 Prisma.$queryRawUnsafe（混合方案）');
    log.debug('参数:', {
      vectorLength: vectorString.length,
      pdfId: pdfId || 'all',
      threshold,
      topK,
    });

    // 修改点：根据实际列名调整（三种可能的列名）
    let sql = `
      SELECT 
        dc.id,
        dc.pdf_id as "pdfId",
        dc.chunk_index as "chunkIndex", 
        dc.content,
        dc.page_number as "pageNumber",
        dc.token_count as "tokenCount",
        dc.metadata,
        p.name as "pdfName",
        p."filePath" as "pdfPath",
        1 - (dc.embedding <=> $1::vector) as similarity
      FROM document_chunks dc
      JOIN pdfs p ON dc.pdf_id = p.id
      WHERE dc.embedding IS NOT NULL
    `;

    const params = [vectorString];
    let paramIndex = 2;

    if (pdfId) {
      sql += ` AND p.id = $${paramIndex}`;
      params.push(pdfId);
      paramIndex++;
    }

    sql += ` AND (1 - (dc.embedding <=> $1::vector)) >= $${paramIndex}`;
    params.push(threshold);
    paramIndex++;

    sql += `
      ORDER BY dc.embedding <=> $1::vector
      LIMIT $${paramIndex}
    `;
    params.push(topK);

    log.debug('最终 SQL:', sql.substring(0, 300) + '...');
    log.debug(
      '参数列表:',
      params.map((p, i) =>
        i === 0 ? `$${i + 1}: [向量,长度=${p.length}]` : `$${i + 1}: ${p}`
      )
    );

    const results = await prisma.$queryRawUnsafe(sql, ...params);

    log.debug(`找到 ${results.length} 个相似块`);

 
    const formattedResults = results.map((row) => ({
      id: row.id,
      pdfId: row.pdfId,
      pdfName: row.pdfName,
      pdfPath: row.pdfPath,
      chunkIndex: row.chunkIndex,
      content: row.content,
      pageNumber: row.pageNumber,
      tokenCount: row.tokenCount,
      // ✅ 添加空值检查和类型转换
      similarity: (() => {
        if (row.similarity === null || row.similarity === undefined) {
          return 0;
        }
        const num = Number(row.similarity);
        if (isNaN(num)) {
          return 0;
        }
        return parseFloat(num.toFixed(4));
      })(),
      metadata: includeMetadata ? row.metadata : undefined,
    }));

    if (formattedResults.length > 0) {
      log.debug('检索结果摘要:');
      formattedResults.forEach((r, i) => {
        log.debug(
          `  ${i + 1}. 相似度: ${r.similarity}, 页码: ${r.pageNumber || 'N/A'}, 长度: ${r.content.length}`
        );
      });
    } else {
      log.debug('未找到满足条件的结果');
    }

    return formattedResults;
  } catch (error) {
    console.error('检索失败:', error);
    console.error('错误详情:', error.message);
    console.error('错误代码:', error.code);
    console.error('错误堆栈:', error.stack);

    throw new Error(`向量检索失败: ${error.message}`);
  }
}

export async function hybridSearch(query, options = {}) {
  const {
    pdfId = null,
    topK = DEFAULT_TOP_K,
    vectorWeight = 0.7,
    keywordWeight = 0.3,
  } = options;

  log.debug('混合检索开始...');

  try {
    const vectorResults = await searchSimilarChunks(query, {
      pdfId,
      topK: topK * 2,
      threshold: 0.5,
    });

    const keywords = query.split(/\s+/).filter((k) => k.length > 1);

    let keywordResults = [];
    if (keywords.length > 0) {
      const whereCondition = {
        content: {
          contains: keywords.join(' '),
          mode: 'insensitive',
        },
      };

      if (pdfId) {
        whereCondition.pdfId = pdfId;
      }

      keywordResults = await prisma.documentChunk.findMany({
        where: whereCondition,
        include: {
          pdf: {
            select: {
              name: true,
              filePath: true,
            },
          },
        },
        take: topK * 2,
      });
    }

    const combinedMap = new Map();

    vectorResults.forEach((result) => {
      combinedMap.set(result.id, {
        ...result,
        vectorScore: result.similarity,
        keywordScore: 0,
        finalScore: result.similarity * vectorWeight,
      });
    });

    keywordResults.forEach((result) => {
      const keywordScore = calculateKeywordScore(result.content, keywords);

      if (combinedMap.has(result.id)) {
        const existing = combinedMap.get(result.id);
        existing.keywordScore = keywordScore;
        existing.finalScore =
          existing.vectorScore * vectorWeight + keywordScore * keywordWeight;
      } else {
        combinedMap.set(result.id, {
          id: result.id,
          pdfId: result.pdfId,
          pdfName: result.pdf.name,
          pdfPath: result.pdf.filePath,
          chunkIndex: result.chunkIndex,
          content: result.content,
          pageNumber: result.pageNumber,
          tokenCount: result.tokenCount,
          vectorScore: 0,
          keywordScore: keywordScore,
          finalScore: keywordScore * keywordWeight,
        });
      }
    });

    const finalResults = Array.from(combinedMap.values())
      .sort((a, b) => b.finalScore - a.finalScore)
      .slice(0, topK);

    log.debug(`混合检索完成，返回 ${finalResults.length} 个结果`);

    return finalResults;
  } catch (error) {
    console.error('混合检索失败:', error);
    throw error;
  }
}

function calculateKeywordScore(content, keywords) {
  if (!keywords || keywords.length === 0) return 0;

  const lowerContent = content.toLowerCase();
  let matchCount = 0;

  keywords.forEach((keyword) => {
    const regex = new RegExp(keyword.toLowerCase(), 'g');
    const matches = lowerContent.match(regex);
    if (matches) {
      matchCount += matches.length;
    }
  });

  return Math.min(matchCount / (keywords.length * 3), 1);
}

export default {
  searchSimilarChunks,
  hybridSearch,
};
