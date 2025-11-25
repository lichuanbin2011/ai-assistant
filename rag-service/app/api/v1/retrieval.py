"""
============================================================================
检索 API 路由
============================================================================

文件位置：
  rag-service/app/api/v1/retrieval.py

文件作用：
  提供向量检索（Vector Retrieval）API 接口

主要功能：
  1. 向量检索 - 根据查询检索相关文档块
  2. 查询重写 - 优化查询以提高检索效果（可选）
  3. 相似度过滤 - 过滤低相关度结果
  4. Top-K 检索 - 返回最相关的 K 个结果

检索流程：
  用户查询 → 查询重写（可选） → 向量化 → 相似度计算 
  → 排序 → Top-K 过滤 → 阈值过滤 → 返回结果

技术栈：
  - FastAPI（Web 框架）
  - PostgreSQL + pgvector（向量数据库）
  - Sentence Transformers（向量化模型）

API 端点：
  - POST /api/v1/retrieval/search - 向量检索

依赖文件：
  - app/models/schemas.py（数据模型）
  - app/core/rag/query_rewrite.py（查询重写）
  - app/core/rag/retrieval.py（检索逻辑）

============================================================================
"""
from fastapi import APIRouter, HTTPException, status  # FastAPI 路由和异常
from loguru import logger  # 日志记录器

from app.models.schemas import (
    RetrievalRequest,  # 检索请求模型
    RetrievalResponse,  # 检索响应模型
    ChunkResult,  # 文档块结果模型
)
from app.core.rag.query_rewrite import get_query_rewriter  # 查询重写器
from app.core.rag.retrieval import get_retriever  # 检索器

# 创建路由器
router = APIRouter()


# ============================================================================
# 向量检索接口
# ============================================================================

@router.post("/search", response_model=RetrievalResponse)
async def search_documents(request: RetrievalRequest):
    """
    向量检索文档
    
    功能说明：
      - 根据查询文本检索相关文档块
      - 支持查询重写（优化检索效果）
      - 支持 Top-K 检索（返回最相关的 K 个结果）
      - 支持相似度阈值过滤（过滤低相关度结果）
    
    检索流程：
      1. 查询重写（可选）- 优化查询文本
      2. 查询向量化 - 将查询转换为向量
      3. 相似度计算 - 计算查询向量和文档向量的余弦相似度
      4. 排序 - 按相似度降序排列
      5. Top-K 过滤 - 返回最相关的 K 个结果
      6. 阈值过滤 - 过滤低于阈值的结果
    
    Args:
        request: 检索请求
            {
                "query": "什么是机器学习？",
                "pdf_id": "uuid",  # 可选，指定 PDF
                "top_k": 5,  # 可选，默认 5
                "threshold": 0.5  # 可选，默认 0.5
            }

    Returns:
        检索响应：
        {
            "success": true,
            "chunks": [
                {
                    "id": "uuid",
                    "pdf_id": "uuid",
                    "pdf_name": "document.pdf",
                    "chunk_index": 0,
                    "content": "文本内容...",
                    "page_number": 1,
                    "similarity": 0.85,
                    "token_count": 100
                }
            ],
            "total": 5,
            "query_rewrite": {
                "original_query": "什么是机器学习？",
                "final_query": "机器学习 定义 概念",
                "query_type": "definition"
            }
        }
    
    参数说明：
      - query: 查询文本（必填）
      - pdf_id: PDF ID（可选，如果指定则只在该 PDF 中检索）
      - top_k: 返回结果数量（默认 5，范围 1-100）
      - threshold: 相似度阈值（默认 0.5，范围 0-1）
    
    相似度说明：
      - 1.0: 完全相同
      - 0.8-1.0: 高度相关
      - 0.6-0.8: 中度相关
      - 0.4-0.6: 低度相关
      - 0.0-0.4: 不相关
    
    使用示例：
        ```bash
        curl -X POST http://localhost:8001/api/v1/retrieval/search \
          -H "Content-Type: application/json" \
          -d '{
            "query": "什么是机器学习？",
            "top_k": 5,
            "threshold": 0.6
          }'
        ```
    
    Raises:
        HTTPException 400: 参数错误（查询为空、top_k 超出范围等）
        HTTPException 500: 检索失败（向量化失败、数据库查询失败等）
    """
    try:
        logger.info(f"收到检索请求: query_len={len(request.query)}, top_k={request.top_k}")

        # ========== 初始化服务 ==========
        query_rewriter = get_query_rewriter()  # 查询重写器
        retriever = get_retriever()  # 检索器

        # ====================================================================
        # 1. 查询重写（可选）
        # ====================================================================
        # 功能说明：
        #   - 优化用户查询，提高检索效果
        #   - 例如："这个文档讲了什么？" → "文档主要内容 核心观点 关键信息"
        #   - 如果查询重写失败，使用原始查询
        rewrite_result = None  # 查询重写结果
        final_query = request.query  # 最终查询（初始为原始查询）

        if query_rewriter.enabled:
            # 查询重写器已启用
            try:
                # 执行查询重写
                rewrite_result = await query_rewriter.rewrite(request.query)
                # 说明：
                #   - rewrite 返回：
                #     {
                #       "original_query": "什么是机器学习？",
                #       "final_query": "机器学习 定义 概念",
                #       "query_type": "definition"
                #     }
                
                final_query = rewrite_result["final_query"]  # 使用重写后的查询
                logger.info(f"查询重写: {request.query} → {final_query}")
            
            except Exception as e:
                # 查询重写失败，使用原始查询
                logger.warning(f"查询重写失败，使用原始查询: {e}")
                final_query = request.query

        # ====================================================================
        # 2. 向量检索
        # ====================================================================
        # 功能说明：
        #   - 将查询向量化
        #   - 计算查询向量和文档向量的余弦相似度
        #   - 返回最相关的 Top-K 个结果
        chunks = await retriever.search(
            query=final_query,  # 查询文本（重写后或原始）
            pdf_id=request.pdf_id,  # PDF ID（可选）
            top_k=request.top_k,  # 返回结果数量
            threshold=request.threshold,  # 相似度阈值
        )
        # 说明：
        #   - search 返回：
        #     [
        #       {
        #         "id": "uuid",
        #         "pdf_id": "uuid",
        #         "pdf_name": "document.pdf",
        #         "chunk_index": 0,
        #         "content": "文本内容...",
        #         "page_number": 1,
        #         "similarity": 0.85,
        #         "token_count": 100
        #       }
        #     ]
        #   - 已按相似度降序排列
        #   - 已过滤低于阈值的结果

        logger.info(f"检索完成: 找到 {len(chunks)} 个结果")

        # ====================================================================
        # 3. 格式化响应
        # ====================================================================
        # 确保字段名匹配（从 retrieval.py 返回的是下划线格式）
        # 说明：
        #   - retrieval.py 返回的字段名是下划线格式（pdf_id, chunk_index）
        #   - ChunkResult 模型也使用下划线格式
        #   - 直接映射即可
        chunk_results = [
            ChunkResult(
                id=chunk["id"],  # 文档块 ID
                pdf_id=chunk["pdf_id"],  # 已经是下划线格式
                pdf_name=chunk["pdf_name"],  # PDF 名称
                chunk_index=chunk["chunk_index"],  # 分块索引
                content=chunk["content"],  # 文本内容
                page_number=chunk.get("page_number"),  # 页码（可选）
                similarity=chunk["similarity"],  # 相似度（0-1）
                token_count=chunk["token_count"],  # Token 数量
            )
            for chunk in chunks
        ]

        # 构建响应
        response = RetrievalResponse(
            success=True,  # 操作成功
            chunks=chunk_results,  # 文档块列表
            total=len(chunk_results),  # 结果总数
            query_rewrite=rewrite_result,  # 查询重写结果（可选）
        )

        return response

    # ====================================================================
    # 异常处理
    # ====================================================================
    except ValueError as e:
        # 参数错误
        logger.error(f"参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 其他异常
        logger.error(f"检索失败: {e}")
        logger.exception(e)  # 添加详细堆栈信息
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检索失败: {str(e)}"
        )


# ============================================================================
# 向量检索原理
# ============================================================================
# 1. 向量化
#    - 将查询文本转换为向量（例如：1024 维）
#    - 使用 Sentence Transformers 模型
#
# 2. 相似度计算
#    - 计算查询向量和文档向量的余弦相似度
#    - 公式：similarity = (A · B) / (||A|| * ||B||)
#    - 范围：-1 到 1（通常归一化到 0-1）
#
# 3. 余弦相似度
#    - 衡量两个向量的方向相似度
#    - 不考虑向量的长度，只考虑方向
#    - 适合文本相似度计算
#
# 4. Top-K 检索
#    - 返回相似度最高的 K 个结果
#    - 使用堆排序或快速选择算法
#
# 5. 阈值过滤
#    - 过滤低于阈值的结果
#    - 避免返回不相关的内容

# ============================================================================
# 查询重写说明
# ============================================================================
# 查询重写的目的：
#   - 优化用户查询，提高检索效果
#   - 提取关键词，去除停用词
#   - 扩展同义词，增加召回率
#
# 查询类型：
#   - definition: 定义类查询（"什么是...？"）
#   - explanation: 解释类查询（"为什么...？"）
#   - comparison: 比较类查询（"A 和 B 的区别？"）
#   - procedure: 步骤类查询（"如何...？"）
#   - general: 一般查询
#
# 重写策略：
#   - definition: 提取核心概念 + "定义"、"概念"
#   - explanation: 提取核心概念 + "原因"、"解释"
#   - comparison: 提取对比对象 + "区别"、"对比"
#   - procedure: 提取核心动作 + "步骤"、"方法"
#
# 示例：
#   原始查询："什么是机器学习？"
#   查询类型：definition
#   重写查询："机器学习 定义 概念"

# ============================================================================
# 相似度阈值建议
# ============================================================================
# 阈值设置：
#   - 0.8-1.0: 严格模式（只返回高度相关的结果）
#   - 0.6-0.8: 标准模式（返回中度以上相关的结果）
#   - 0.4-0.6: 宽松模式（返回低度以上相关的结果）
#   - 0.0-0.4: 极宽松模式（返回所有结果）
#
# 推荐值：
#   - RAG 对话：0.6-0.7（保证回答质量）
#   - 文档搜索：0.5-0.6（增加召回率）
#   - 精确匹配：0.8-0.9（只返回高度相关）

# ============================================================================
# Top-K 设置建议
# ============================================================================
# Top-K 设置：
#   - 1-3: 精确回答（适合问答场景）
#   - 3-5: 标准回答（适合 RAG 对话）
#   - 5-10: 详细回答（适合文档搜索）
#   - 10+: 全面回答（适合探索性搜索）
#
# 推荐值：
#   - RAG 对话：3-5（平衡质量和上下文长度）
#   - 文档搜索：5-10（提供更多选择）
#   - 问答系统：1-3（快速精确回答）

# ============================================================================
# 检索性能优化
# ============================================================================
# 1. 向量索引
#    - 使用 pgvector 的 HNSW 索引
#    - 加速相似度计算
#    - 牺牲少量精度换取速度
#
# 2. 缓存
#    - 缓存查询向量
#    - 缓存检索结果
#    - 使用 Redis 或内存缓存
#
# 3. 批量检索
#    - 一次检索多个查询
#    - 减少数据库查询次数
#
# 4. 异步处理
#    - 使用异步 I/O
#    - 提高并发性能
#
# 5. 预过滤
#    - 先过滤 PDF ID
#    - 再计算相似度
#    - 减少计算量

# ============================================================================
# 错误处理说明
# ============================================================================
# 1. 查询为空（400）
#    错误：ValueError("查询不能为空")
#    原因：request.query 为空字符串
#    解决：检查输入
#
# 2. Top-K 超出范围（400）
#    错误：ValueError("top_k 必须在 1-100 之间")
#    原因：request.top_k < 1 或 > 100
#    解决：调整 top_k 值
#
# 3. 阈值超出范围（400）
#    错误：ValueError("threshold 必须在 0-1 之间")
#    原因：request.threshold < 0 或 > 1
#    解决：调整 threshold 值
#
# 4. 向量化失败（500）
#    错误：Exception("向量化失败")
#    原因：模型加载失败、输入格式错误等
#    解决：检查模型状态，重试
#
# 5. 数据库查询失败（500）
#    错误：Exception("数据库查询失败")
#    原因：数据库连接失败、SQL 错误等
#    解决：检查数据库状态，重试

# ============================================================================
# 使用场景
# ============================================================================
# 1. RAG 对话
#    - 检索相关文档块
#    - 构建上下文
#    - 生成回答
#
# 2. 文档搜索
#    - 搜索相关文档
#    - 展示搜索结果
#    - 支持翻页
#
# 3. 问答系统
#    - 精确回答问题
#    - 提供来源引用
#    - 支持多轮对话
#
# 4. 语义搜索
#    - 理解用户意图
#    - 返回语义相关的结果
#    - 不依赖关键词匹配
