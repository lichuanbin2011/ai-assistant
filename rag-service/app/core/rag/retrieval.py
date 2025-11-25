"""
============================================================================
向量检索模块
============================================================================

文件位置：
  rag-service/app/core/rag/retrieval.py

文件作用：
  提供向量检索（Vector Retrieval）功能，根据查询检索相关文档块

主要功能：
  1. 向量检索 - 根据查询向量检索相似文档块
  2. 智能检索 - 多重回退策略，保证检索结果
  3. 相似度计算 - 使用余弦相似度计算
  4. 结果过滤 - 根据阈值和 Top-K 过滤

检索原理：
  - 查询向量化：将查询文本转换为向量
  - 相似度计算：计算查询向量和文档向量的余弦相似度
  - 排序：按相似度降序排列
  - 过滤：根据阈值和 Top-K 过滤结果

技术栈：
  - PostgreSQL + pgvector（向量数据库）
  - Sentence Transformers（向量化模型）
  - 余弦相似度（Cosine Similarity）

依赖文件：
  - app/core/database.py（数据库连接）
  - app/core/config.py（配置管理）
  - app/services/embedding.py（向量化服务）

============================================================================
"""
from typing import List, Dict, Any, Optional  # 类型注解
from loguru import logger  # 日志记录器

from app.core.database import get_database  # 数据库连接
from app.core.config import get_settings  # 配置管理
from app.services.embedding import get_embedding_service  # 向量化服务

settings = get_settings()  # 获取配置


# ============================================================================
# 向量检索器类
# ============================================================================

class VectorRetriever:
    """
    向量检索器
    
    功能说明：
      - 根据查询向量检索相似文档块
      - 支持 Top-K 检索和阈值过滤
      - 支持按 PDF 过滤
      - 支持智能检索（多重回退策略）
    
    检索原理：
      1. 查询向量化：将查询文本转换为向量
      2. 相似度计算：计算查询向量和文档向量的余弦相似度
      3. 排序：按相似度降序排列
      4. 过滤：根据阈值和 Top-K 过滤结果
    
    余弦相似度：
      - 公式：similarity = 1 - (A <=> B)
      - <=>：pgvector 的余弦距离操作符
      - 范围：0-1（1 表示完全相同，0 表示完全不同）
    
    使用示例：
        ```python
        retriever = VectorRetriever()
        results = await retriever.search(
            query="什么是机器学习？",
            top_k=5,
            threshold=0.6
        )
        ```
    """

    def __init__(self):
        """
        初始化向量检索器
        
        功能说明：
          - 获取数据库连接
          - 获取向量化服务
          - 记录初始化日志
        """
        self.db = get_database()  # 数据库连接
        self.embedding_service = get_embedding_service()  # 向量化服务
        logger.info("向量检索器初始化完成")

    async def search(
            self,
            query: str,  # 查询文本
            pdf_id: Optional[str] = None,  # PDF ID（可选）
            top_k: int = None,  # 返回结果数量
            threshold: float = None,  # 相似度阈值
    ) -> List[Dict[str, Any]]:
        """
        向量检索
        
        功能说明：
          - 将查询文本向量化
          - 计算查询向量和文档向量的余弦相似度
          - 按相似度降序排列
          - 根据阈值和 Top-K 过滤结果
        
        检索流程：
          1. 查询向量化（转换为向量）
          2. 构建 SQL 查询（计算相似度）
          3. 执行查询（从数据库检索）
          4. 格式化结果（映射字段名）
          5. 返回结果列表
        
        Args:
            query: 查询文本
                - 类型：字符串
                - 示例："什么是机器学习？"
            
            pdf_id: PDF ID（可选）
                - 类型：字符串
                - 用途：只在指定 PDF 中检索
                - 示例："123e4567-e89b-12d3-a456-426614174000"
            
            top_k: 返回结果数量（可选）
                - 类型：整数
                - 默认：从配置读取（通常 5）
                - 范围：1-100
            
            threshold: 相似度阈值（可选）
                - 类型：浮点数
                - 默认：从配置读取（通常 0.5）
                - 范围：0-1
                - 说明：只返回相似度 >= 阈值的结果

        Returns:
            检索结果列表：
            [
                {
                    "id": "uuid",
                    "pdf_id": "uuid",
                    "pdf_name": "document.pdf",
                    "chunk_index": 0,
                    "content": "文本内容...",
                    "page_number": 1,
                    "token_count": 100,
                    "similarity": 0.85,
                    "metadata": {}
                }
            ]
        
        字段说明：
          - id: 文档块 ID
          - pdf_id: PDF ID
          - pdf_name: PDF 名称
          - chunk_index: 分块索引
          - content: 文本内容
          - page_number: 页码
          - token_count: Token 数量
          - similarity: 相似度（0-1）
          - metadata: 元数据
        
        使用示例：
            ```python
            retriever = VectorRetriever()
            
            # 基本检索
            results = await retriever.search("什么是机器学习？")
            
            # 指定 PDF
            results = await retriever.search(
                "什么是机器学习？",
                pdf_id="123e4567"
            )
            
            # 自定义参数
            results = await retriever.search(
                "什么是机器学习？",
                top_k=10,
                threshold=0.7
            )
            ```
        
        Raises:
            ValueError: 向量检索失败
        """
        # ========== 1. 设置默认参数 ==========
        top_k = top_k or settings.RETRIEVAL_TOP_K  # 默认从配置读取
        threshold = threshold or settings.SIMILARITY_THRESHOLD  # 默认从配置读取

        logger.info(f"开始向量检索: query_len={len(query)}, top_k={top_k}")

        try:
            # ========== 2. 查询向量化 ==========
            query_vector = await self.embedding_service.embed_single(query)
            # 说明：
            #   - embed_single: 将查询文本转换为向量
            #   - 返回：[0.1, 0.2, 0.3, ...] (1024 维)
            
            # 转换为 PostgreSQL 向量格式
            vector_str = f"[{','.join(map(str, query_vector))}]"
            # 说明：
            #   - PostgreSQL 向量格式：[0.1,0.2,0.3,...]
            #   - 使用逗号分隔，没有空格

            # ========== 3. 构建 SQL 查询 ==========
            # 使用实际的数据库字段名（驼峰命名）
            sql = """
                SELECT 
                    dc.id,                                              -- 文档块 ID
                    dc.pdf_id as "pdfId",                              -- PDF ID（驼峰命名）
                    dc.chunk_index as "chunkIndex",                    -- 分块索引
                    dc.content,                                         -- 文本内容
                    dc.page_number as "pageNumber",                    -- 页码
                    dc.token_count as "tokenCount",                    -- Token 数量
                    dc.metadata,                                        -- 元数据
                    p.name as "pdfName",                               -- PDF 名称
                    p."filePath" as "pdfPath",                         -- PDF 路径
                    1 - (dc.embedding <=> CAST(:vec AS vector)) as similarity  -- 余弦相似度
                FROM document_chunks dc
                JOIN pdfs p ON dc.pdf_id = p.id                        -- 关联 PDF 表
                WHERE dc.embedding IS NOT NULL                          -- 过滤未向量化的块
            """
            # 说明：
            #   - dc: document_chunks 表别名
            #   - p: pdfs 表别名
            #   - <=>: pgvector 的余弦距离操作符
            #   - 1 - 距离 = 相似度（范围 0-1）
            #   - CAST(:vec AS vector): 将字符串转换为向量类型

            # 初始化参数
            params = {"vec": vector_str}

            # ========== 4. 添加 PDF 过滤 ==========
            if pdf_id:
                sql += " AND p.id = :pdf_id"
                params["pdf_id"] = pdf_id

            # ========== 5. 添加相似度过滤和排序 ==========
            # 添加相似度过滤和排序
            sql += """
                AND (1 - (dc.embedding <=> CAST(:vec AS vector))) >= :threshold
                ORDER BY dc.embedding <=> CAST(:vec AS vector)
                LIMIT :top_k
            """
            # 说明：
            #   - 相似度过滤：只返回 similarity >= threshold 的结果
            #   - 排序：按余弦距离升序（相似度降序）
            #   - 限制：只返回前 top_k 个结果
            
            params["threshold"] = threshold
            params["top_k"] = top_k

            logger.debug(f"执行 SQL: {sql[:200]}...")
            logger.debug(f"参数: pdf_id={pdf_id}, threshold={threshold}, top_k={top_k}")

            # ========== 6. 执行查询 ==========
            rows = await self.db.fetch(sql, **params)
            # 说明：
            #   - fetch: 执行查询，返回所有行
            #   - **params: 展开参数字典

            # ========== 7. 格式化结果 ==========
            # 格式化结果，映射到 API 响应格式（下划线命名）
            results = [
                {
                    "id": row["id"],  # 文档块 ID
                    "pdf_id": row["pdfId"],  # ✅ 从驼峰转下划线
                    "pdf_name": row["pdfName"],  # PDF 名称
                    "chunk_index": row["chunkIndex"],  # 分块索引
                    "content": row["content"],  # 文本内容
                    "page_number": row["pageNumber"],  # 页码
                    "token_count": row["tokenCount"],  # Token 数量
                    "similarity": float(row["similarity"]),  # 相似度（转换为浮点数）
                    "metadata": row.get("metadata", {}),  # 元数据（默认空字典）
                }
                for row in rows
            ]
            # 说明：
            #   - 数据库字段名：驼峰命名（pdfId, chunkIndex）
            #   - API 响应字段名：下划线命名（pdf_id, chunk_index）
            #   - 需要映射转换

            logger.info(f"检索完成: 找到 {len(results)} 个结果")

            return results

        except Exception as e:
            # ========== 8. 异常处理 ==========
            logger.error(f"向量检索失败: {e}")
            logger.exception(e)  # 输出完整堆栈
            raise ValueError(f"向量检索失败: {str(e)}")

    async def smart_retrieval(
            self,
            query: str,  # 查询文本
            pdf_id: str,  # PDF ID
            pdf_record: Dict[str, Any]  # PDF 记录
    ) -> List[Dict[str, Any]]:
        """
        智能检索（多重回退策略）
        
        功能说明：
          - 使用多重回退策略保证检索结果
          - 策略 1：标准检索（阈值 0.6）
          - 策略 2：降低阈值（阈值 0.4）
          - 策略 3：均匀采样（每隔 step 个块取一个）
          - 策略 4：取前 10 个块（最终回退）
        
        使用场景：
          - 查询与文档相关度较低
          - 文档向量化不完整
          - 需要保证一定数量的结果
        
        回退策略：
          1. 标准检索（阈值 0.6，Top-K 5）
             - 如果结果 >= 3，返回
          
          2. 降低阈值（阈值 0.4，Top-K 8）
             - 如果结果 >= 3，返回
          
          3. 均匀采样（每隔 step 个块取一个，最多 10 个）
             - step = total_chunks // 10
             - 如果有结果，返回
          
          4. 取前 10 个块（最终回退）
             - 保证一定有结果

        Args:
            query: 查询文本
            pdf_id: PDF ID
            pdf_record: PDF 记录
                {
                    "id": "uuid",
                    "name": "document.pdf",
                    "total_chunks": 100,
                    "totalChunks": 100  # 兼容驼峰命名
                }

        Returns:
            检索结果列表（格式同 search 方法）
        
        使用示例：
            ```python
            retriever = VectorRetriever()
            results = await retriever.smart_retrieval(
                query="什么是机器学习？",
                pdf_id="123e4567",
                pdf_record={"total_chunks": 100}
            )
            ```
        """
        logger.info(f"智能检索开始: pdf_id={pdf_id}")

        # ====================================================================
        # 策略1：标准检索（阈值 0.6）
        # ====================================================================
        # 功能说明：
        #   - 使用标准阈值（0.6）
        #   - 返回前 5 个结果
        #   - 如果结果 >= 3，认为成功
        chunks = await self.search(query, pdf_id=pdf_id, top_k=5, threshold=0.6)
        if len(chunks) >= 3:
            logger.info("策略1成功: 标准检索")
            return chunks

        # ====================================================================
        # 策略2：降低阈值（0.4）
        # ====================================================================
        # 功能说明：
        #   - 降低阈值到 0.4（更宽松）
        #   - 返回前 8 个结果（增加数量）
        #   - 如果结果 >= 3，认为成功
        logger.warning("策略1结果不足，降低阈值到 0.4")
        chunks = await self.search(query, pdf_id=pdf_id, top_k=8, threshold=0.4)
        if len(chunks) >= 3:
            logger.info("策略2成功: 降低阈值")
            return chunks

        # ====================================================================
        # 策略3：均匀采样
        # ====================================================================
        # 功能说明：
        #   - 不使用向量检索
        #   - 均匀采样文档块（每隔 step 个块取一个）
        #   - 最多返回 10 个块
        logger.warning("策略2仍不足，使用均匀采样")

        # ========== 1. 计算采样步长 ==========
        # 从 pdf_record 获取 total_chunks（注意字段名）
        total_chunks = pdf_record.get("total_chunks") or pdf_record.get("totalChunks", 0)
        # 说明：
        #   - 兼容下划线命名（total_chunks）和驼峰命名（totalChunks）
        #   - 默认值：0
        
        step = max(1, total_chunks // 10)  # 步长 = 总块数 / 10（至少为 1）
        # 说明：
        #   - 如果总块数 = 100，步长 = 10（每隔 10 个块取一个）
        #   - 如果总块数 = 50，步长 = 5（每隔 5 个块取一个）

        # ========== 2. 查询所有块 ==========
        # 策略3 使用命名参数，映射字段名
        sql = """
            SELECT 
                id, 
                pdf_id as "pdfId",                  -- PDF ID（驼峰命名）
                chunk_index as "chunkIndex",        -- 分块索引
                content,                             -- 文本内容
                page_number as "pageNumber",        -- 页码
                token_count as "tokenCount",        -- Token 数量
                metadata                             -- 元数据
            FROM document_chunks
            WHERE pdf_id = :pdf_id
            ORDER BY chunk_index                     -- 按索引排序
            LIMIT 100                                -- 最多查询 100 个块
        """

        rows = await self.db.fetch(sql, pdf_id=pdf_id)

        # ========== 3. 均匀采样 ==========
        # 格式化结果，统一字段名
        sampled = []
        for i, row in enumerate(rows):
            if i % step == 0:  # 每隔 step 个块取一个
                sampled.append({
                    "id": row["id"],
                    "pdf_id": row["pdfId"],  # 从驼峰转下划线
                    "chunk_index": row["chunkIndex"],
                    "content": row["content"],
                    "page_number": row["pageNumber"],
                    "token_count": row["tokenCount"],
                    "metadata": row.get("metadata", {}),
                    "similarity": 0.0,  # 采样结果没有相似度
                    "pdf_name": pdf_record.get("name", ""),  # 从 pdf_record 获取
                })
                if len(sampled) >= 10:  # 最多 10 个块
                    break

        if sampled:
            logger.info(f"策略3成功: 均匀采样 {len(sampled)} 个块")
            return sampled

        # ====================================================================
        # 策略4：取前10个块（最终回退）
        # ====================================================================
        # 功能说明：
        #   - 不使用向量检索
        #   - 直接返回前 10 个块
        #   - 保证一定有结果
        logger.warning("策略3失败，使用最终回退")

        # ========== 1. 查询前 10 个块 ==========
        # 策略4 使用命名参数，映射字段名
        sql = """
            SELECT 
                id, 
                pdf_id as "pdfId",                  -- PDF ID
                chunk_index as "chunkIndex",        -- 分块索引
                content,                             -- 文本内容
                page_number as "pageNumber",        -- 页码
                token_count as "tokenCount",        -- Token 数量
                metadata                             -- 元数据
            FROM document_chunks
            WHERE pdf_id = :pdf_id
            ORDER BY chunk_index                     -- 按索引排序
            LIMIT 10                                 -- 最多 10 个块
        """

        rows = await self.db.fetch(sql, pdf_id=pdf_id)

        # ========== 2. 格式化结果 ==========
        # 格式化结果
        fallback = [
            {
                "id": row["id"],
                "pdf_id": row["pdfId"],  # 从驼峰转下划线
                "chunk_index": row["chunkIndex"],
                "content": row["content"],
                "page_number": row["pageNumber"],
                "token_count": row["tokenCount"],
                "metadata": row.get("metadata", {}),
                "similarity": 0.0,  # 没有相似度
                "pdf_name": pdf_record.get("name", ""),  # 从 pdf_record 获取
            }
            for row in rows
        ]

        logger.info(f"策略4完成: 取前 {len(fallback)} 个块")
        return fallback


# ============================================================================
# 工厂函数（单例模式）
# ============================================================================

# 单例模式（避免重复创建）
_retriever_instance: Optional[VectorRetriever] = None  # 全局单例实例


def get_retriever() -> VectorRetriever:
    """
    获取检索器实例（单例）
    
    功能说明：
      - 使用单例模式，避免重复创建
      - 第一次调用时创建实例
      - 后续调用返回同一个实例
    
    Returns:
        VectorRetriever: 向量检索器实例
    
    使用示例：
        ```python
        retriever = get_retriever()
        results = await retriever.search("什么是机器学习？")
        ```
    """
    global _retriever_instance

    if _retriever_instance is None:
        _retriever_instance = VectorRetriever()

    return _retriever_instance


# ============================================================================
# 余弦相似度详解
# ============================================================================
# 余弦相似度（Cosine Similarity）：
#   - 衡量两个向量的方向相似度
#   - 不考虑向量的长度，只考虑方向
#   - 适合文本相似度计算
#
# 公式：
#   similarity = cos(θ) = (A · B) / (||A|| * ||B||)
#   其中：
#     - A, B: 两个向量
#     - A · B: 向量点积
#     - ||A||, ||B||: 向量的模（长度）
#     - θ: 两个向量的夹角
#
# pgvector 实现：
#   - <=>: 余弦距离操作符
#   - 余弦距离 = 1 - 余弦相似度
#   - 余弦相似度 = 1 - 余弦距离
#
# 相似度范围：
#   - 1.0: 完全相同（夹角 0°）
#   - 0.8-1.0: 高度相关
#   - 0.6-0.8: 中度相关
#   - 0.4-0.6: 低度相关
#   - 0.0-0.4: 不相关
#   - 0.0: 完全不同（夹角 90°）

# ============================================================================
# 智能检索策略详解
# ============================================================================
# 策略 1：标准检索
#   - 阈值：0.6（中度相关以上）
#   - Top-K：5
#   - 成功条件：结果 >= 3
#   - 适用场景：查询与文档高度相关
#
# 策略 2：降低阈值
#   - 阈值：0.4（低度相关以上）
#   - Top-K：8
#   - 成功条件：结果 >= 3
#   - 适用场景：查询与文档中度相关
#
# 策略 3：均匀采样
#   - 方法：每隔 step 个块取一个
#   - step = total_chunks // 10
#   - 最多：10 个块
#   - 适用场景：查询与文档相关度较低
#
# 策略 4：取前 10 个块
#   - 方法：直接返回前 10 个块
#   - 适用场景：最终回退，保证有结果

# ============================================================================
# 性能优化建议
# ============================================================================
# 1. 向量索引
#    - 使用 pgvector 的 HNSW 索引
#    - 加速相似度计算
#    - 创建索引：
#      CREATE INDEX ON document_chunks 
#      USING hnsw (embedding vector_cosine_ops);
#
# 2. 缓存查询向量
#    - 缓存常见查询的向量
#    - 避免重复向量化
#
# 3. 批量检索
#    - 一次检索多个查询
#    - 减少数据库查询次数
#
# 4. 异步并行
#    - 多个查询并行检索
#    - 提高并发性能
#
# 5. 预过滤
#    - 先过滤 PDF ID
#    - 再计算相似度
#    - 减少计算量

# ============================================================================
# 错误处理说明
# ============================================================================
# 1. 向量化失败
#    - 错误：ValueError("向量化失败")
#    - 原因：模型加载失败、输入格式错误
#    - 解决：检查模型状态，重试
#
# 2. 数据库查询失败
#    - 错误：ValueError("向量检索失败")
#    - 原因：数据库连接失败、SQL 错误
#    - 解决：检查数据库状态，重试
#
# 3. 结果为空
#    - 原因：阈值过高、文档不相关
#    - 解决：降低阈值或使用智能检索
#
# 4. 字段名不匹配
#    - 原因：数据库字段名和代码不一致
#    - 解决：检查字段名映射
