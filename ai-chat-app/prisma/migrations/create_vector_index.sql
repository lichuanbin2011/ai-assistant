-- ============================================================================
-- 创建向量相似度搜索索引（修正版）
-- ============================================================================

-- 步骤 1：检查是否有数据
SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;

-- 步骤 2：如果有数据，创建索引
-- 注意：只有在有数据的情况下才能创建 IVFFlat 索引
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 说明：
-- - ivfflat: 倒排文件索引，适合 10K-1M 向量
-- - vector_cosine_ops: 余弦相似度（推荐）
-- - lists = 100: 聚类数量（建议为行数的平方根）

-- 如果数据量更大（> 1M），使用 HNSW 索引：
-- CREATE INDEX document_chunks_embedding_idx 
-- ON document_chunks 
-- USING hnsw (embedding vector_cosine_ops);
