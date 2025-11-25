"""
============================================================================
Embedding API 路由（完全修复版 - 移除错误的异常处理器）
============================================================================

文件位置：
  rag-service/app/api/v1/embed.py

文件作用：
  提供文本向量化（Embedding）API 接口

主要功能：
  1. 单个文本向量化 - 将单个文本转换为向量
  2. 批量文本向量化 - 将多个文本批量转换为向量
  3. 输入验证 - 验证文本不为空
  4. 缓存支持 - 缓存向量化结果

向量化说明：
  - 向量化（Embedding）：将文本转换为数值向量
  - 用途：文本相似度计算、语义搜索、RAG 检索
  - 模型：baai/bge-m3（默认）
  - 维度：1024（默认）

技术栈：
  - FastAPI（Web 框架）
  - Pydantic（数据验证）
  - Sentence Transformers（向量化模型）

API 端点：
  - POST /api/v1/embed - 批量向量化（标准版）
  - POST /api/v1/embed/single - 单个向量化
  - POST /api/v1/embed（别名） - 批量向量化（简化版）

依赖文件：
  - app/models/schemas.py（数据模型）
  - app/services/embedding.py（向量化服务）
  - app/core/config.py（配置管理）

============================================================================
"""
from fastapi import APIRouter, HTTPException, status  # FastAPI 路由和异常
from pydantic import BaseModel, Field, validator  # Pydantic 数据验证
from typing import Optional, List  # 类型注解
from loguru import logger  # 日志记录器

from app.models.schemas import (
    EmbedRequest,  # 批量向量化请求模型
    EmbedResponse,  # 批量向量化响应模型
    EmbeddingData,  # 向量数据模型
    UsageInfo,  # 使用量信息模型
    CacheStats,  # 缓存统计模型
)
from app.services.embedding import get_embedding_service  # 向量化服务
from app.core.config import get_settings  # 配置管理

# 创建路由器
router = APIRouter()
settings = get_settings()  # 获取配置


# ============================================================================
# 请求模型（修复验证器逻辑）
# ============================================================================

class EmbedSingleRequest(BaseModel):
    """
    单个文本向量化请求
    
    功能说明：
      - 定义单个文本向量化的请求格式
      - 使用 Pydantic 验证器验证输入
      - 自动去除空格和空文本
    
    字段说明：
      - text: 要向量化的文本（必填）
      - model: 模型名称（可选，默认使用配置中的模型）
    
    验证规则：
      - text 不能为 None
      - text 不能为空字符串
      - text 去除首尾空格后不能为空
    """
    text: str = Field(..., description="要向量化的文本")
    model: Optional[str] = Field(None, description="模型名称")

    # 先去除空格，再验证
    @validator('text', pre=True)
    def validate_text(cls, v):
        """
        验证文本不为空
        
        功能说明：
          - 在 Pydantic 验证阶段执行
          - 先检查 None，再转换类型，再去除空格，最后验证
        
        Args:
            v: 待验证的值
        
        Returns:
            验证后的文本（去除首尾空格）
        
        Raises:
            ValueError: 文本为空
        
        验证流程：
          1. 检查是否为 None
          2. 转换为字符串（防止传入非字符串类型）
          3. 去除首尾空格
          4. 检查是否为空
        """
        # ========== 1. 先检查是否为 None ==========
        if v is None:
            raise ValueError("文本不能为空")

        # ========== 2. 转换为字符串（防止传入非字符串类型） ==========
        if not isinstance(v, str):
            v = str(v)

        # ========== 3. 去除首尾空格 ==========
        v = v.strip()

        # ========== 4. 检查是否为空 ==========
        if not v:
            raise ValueError("文本不能为空")

        return v


# 为批量请求添加验证器
class EmbedBatchRequest(BaseModel):
    """
    批量文本向量化请求（带验证）
    
    功能说明：
      - 定义批量文本向量化的请求格式
      - 使用 Pydantic 验证器验证输入
      - 自动过滤空文本
    
    字段说明：
      - texts: 文本列表（必填，至少 1 个）
      - model: 模型名称（可选）
    
    验证规则：
      - texts 不能为空列表
      - 过滤掉 None 和空字符串
      - 至少要有 1 个有效文本
    """
    texts: List[str] = Field(..., min_items=1, description="文本列表")
    model: Optional[str] = Field(None, description="模型名称")

    # 先过滤空文本，再验证
    @validator('texts', pre=True)
    def validate_texts(cls, v):
        """
        验证文本列表
        
        功能说明：
          - 过滤掉空文本（None、空字符串、纯空格）
          - 验证至少有 1 个有效文本
        
        Args:
            v: 待验证的文本列表
        
        Returns:
            验证后的文本列表（过滤空文本）
        
        Raises:
            ValueError: 文本列表为空或没有有效文本
        
        验证流程：
          1. 检查列表是否为空
          2. 遍历列表，过滤空文本
          3. 检查是否有有效文本
        """
        # ========== 1. 检查列表是否为空 ==========
        if not v:
            raise ValueError("文本列表不能为空")

        # ========== 2. 过滤空文本 ==========
        filtered = []
        for text in v:
            # 跳过 None
            if text is None:
                continue
            # 转换为字符串
            if not isinstance(text, str):
                text = str(text)
            # 去除空格
            text = text.strip()
            # 添加非空文本
            if text:
                filtered.append(text)

        # ========== 3. 检查是否有有效文本 ==========
        if not filtered:
            raise ValueError("文本列表中没有有效文本")

        return filtered


# ============================================================================
# API 路由
# ============================================================================

@router.post("/embed", response_model=EmbedResponse)
async def embed_texts(request: EmbedRequest):
    """
    批量文本向量化
    
    功能说明：
      - 将多个文本批量转换为向量
      - 支持自定义模型
      - 返回向量、使用量和缓存统计
    
    Args:
        request: 向量化请求，包含多个文本
            {
                "texts": ["文本1", "文本2"],
                "model": "baai/bge-m3"  # 可选
            }

    Returns:
        向量化响应：
        {
            "data": [
                {
                    "embedding": [-0.052, 0.036, ...],
                    "index": 0
                },
                {
                    "embedding": [-0.041, 0.028, ...],
                    "index": 1
                }
            ],
            "model": "baai/bge-m3",
            "usage": {
                "total_tokens": 100
            },
            "cache_stats": {
                "hits": 0,
                "misses": 2,
                "hit_rate": 0.0
            }
        }

    Example:
        ```bash
        curl -X POST http://localhost:8001/api/v1/embed \
          -H "Content-Type: application/json" \
          -d '{
            "texts": ["文本1", "文本2"],
            "model": "baai/bge-m3"
          }'
        ```
    
    Raises:
        HTTPException 400: 文本列表为空或所有文本都为空
        HTTPException 500: 向量化失败
    """
    try:
        logger.info(f"收到批量向量化请求: {len(request.texts)} 个文本")

        # ========== 1. 添加文本验证 ==========
        if not request.texts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文本列表不能为空"
            )

        # ========== 2. 过滤空文本 ==========
        valid_texts = [t for t in request.texts if t and t.strip()]
        if not valid_texts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="所有文本都为空"
            )

        # ========== 3. 记录过滤日志 ==========
        if len(valid_texts) != len(request.texts):
            logger.warning(f"过滤了 {len(request.texts) - len(valid_texts)} 个空文本")

        # ========== 4. 获取向量化服务 ==========
        service = get_embedding_service()

        # ========== 5. 执行向量化 ==========
        result = await service.embed_batch(
            texts=valid_texts,  # 有效文本列表
            model=request.model,  # 模型名称（可选）
            show_progress=True  # 显示进度条
        )
        # 说明：
        #   - embed_batch 返回：
        #     {
        #       "embeddings": [[...], [...]],
        #       "usage": {"total_tokens": 100},
        #       "cache_stats": {"hits": 0, "misses": 2}
        #     }

        # ========== 6. 构建响应 ==========
        data = [
            EmbeddingData(
                embedding=emb,  # 向量
                index=i  # 索引
            )
            for i, emb in enumerate(result["embeddings"])
        ]

        response = EmbedResponse(
            data=data,  # 向量列表
            model=request.model or settings.EMBEDDING_MODEL,  # 使用的模型
            usage=UsageInfo(**result["usage"]),  # 使用量信息
            cache_stats=CacheStats(**result["cache_stats"]) if result.get("cache_stats") else None,  # 缓存统计
        )

        logger.info(f"批量向量化完成: {len(data)} 个向量")

        return response

    # ========== 7. 异常处理 ==========
    except HTTPException:
        # HTTPException 直接抛出
        raise
    except ValueError as e:
        # 参数错误
        logger.error(f"参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 其他异常
        logger.error(f"批量向量化失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"向量化失败: {str(e)}"
        )


# ============================================================================
# 单个文本向量化接口
# ============================================================================

# 修改单个文本向量化端点
@router.post("/single")
async def embed_single_text(request: EmbedSingleRequest):
    """
    单个文本向量化（已修复 Pydantic 验证器）
    
    功能说明：
      - 将单个文本转换为向量
      - 使用 Pydantic 验证器自动验证输入
      - 返回向量和维度信息

    Args:
        request: 单个文本向量化请求
            {
                "text": "什么是机器学习？",
                "model": "baai/bge-m3"  # 可选
            }

    Returns:
        向量化结果：
        {
            "embedding": [-0.052, 0.036, ...],
            "dimension": 1024,
            "model": "baai/bge-m3"
        }

    Example:
        ```bash
        curl -X POST http://localhost:8001/api/v1/embed/single \
          -H "Content-Type: application/json" \
          -d '{
            "text": "什么是机器学习？",
            "model": "baai/bge-m3"
          }'
        ```

    Response:
        ```json
        {
          "embedding": [-0.052, 0.036, ...],
          "dimension": 1024,
          "model": "baai/bge-m3"
        }
        ```
    
    Raises:
        HTTPException 400: 文本为空
        HTTPException 500: 向量化失败
    """
    try:
        # 移除冗余检查（Pydantic 验证器已处理）
        # 说明：
        #   - EmbedSingleRequest 的 validate_text 验证器已经验证了文本
        #   - 这里不需要再次验证
        logger.info(f"单个文本向量化: text_len={len(request.text)}, model={request.model}")

        # ========== 1. 获取向量化服务 ==========
        service = get_embedding_service()

        # ========== 2. 执行向量化 ==========
        embedding = await service.embed_single(
            request.text,  # 文本
            model=request.model  # 模型名称（可选）
        )
        # 说明：
        #   - embed_single 返回单个向量：[-0.052, 0.036, ...]

        # ========== 3. 添加结果验证 ==========
        if not embedding:
            raise ValueError("向量化结果为空")

        logger.info(f"单个文本向量化完成: dimension={len(embedding)}")

        # ========== 4. 返回响应 ==========
        return {
            "embedding": embedding,  # 向量
            "dimension": len(embedding),  # 维度
            "model": request.model or settings.EMBEDDING_MODEL,  # 使用的模型
        }

    # ========== 5. 异常处理 ==========
    except HTTPException:
        # HTTPException 直接抛出
        raise
    # 捕获 Pydantic 验证错误
    except ValueError as e:
        # 参数错误（包括 Pydantic 验证错误）
        logger.error(f"参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 其他异常
        logger.error(f"单个文本向量化失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"向量化失败: {str(e)}"
        )


# ============================================================================
# 批量向量化接口（简化版）
# ============================================================================

# 新增批量向量化端点（使用新的验证器）
@router.post("")
async def embed_batch_texts_alt(request: EmbedBatchRequest):
    """
    批量文本向量化（简化版，使用验证器）
    
    功能说明：
      - 与 /embed 功能相同，但响应格式更简洁
      - 使用 EmbedBatchRequest 验证器自动过滤空文本
      - 返回向量列表和使用量信息

    Args:
        request: 包含文本列表和可选模型的请求
            {
                "texts": ["文本1", "文本2", "文本3"],
                "model": "baai/bge-m3"  # 可选
            }

    Returns:
        向量列表、使用量和缓存统计：
        {
            "data": [
                {
                    "index": 0,
                    "embedding": [-0.052, 0.036, ...],
                    "dimension": 1024
                },
                {
                    "index": 1,
                    "embedding": [-0.041, 0.028, ...],
                    "dimension": 1024
                }
            ],
            "model": "baai/bge-m3",
            "usage": {
                "total_tokens": 100
            },
            "cache_stats": {
                "hits": 0,
                "misses": 2,
                "hit_rate": 0.0
            }
        }

    Example:
        ```bash
        curl -X POST http://localhost:8001/api/v1/embed \
          -H "Content-Type: application/json" \
          -d '{
            "texts": ["文本1", "文本2", "文本3"],
            "model": "baai/bge-m3"
          }'
        ```
    
    Raises:
        HTTPException 400: 文本列表为空或没有有效文本
        HTTPException 500: 向量化失败
    """
    try:
        # ========== 1. 获取向量化服务 ==========
        embedding_service = get_embedding_service()

        logger.info(f"批量向量化（简化版）: {len(request.texts)} 个文本")

        # ========== 2. 执行向量化 ==========
        result = await embedding_service.embed_batch(
            texts=request.texts,  # 文本列表（已通过验证器过滤）
            model=request.model,  # 模型名称（可选）
            show_progress=True  # 显示进度条
        )

        # ========== 3. 构建响应 ==========
        response = {
            "data": [
                {
                    "index": i,  # 索引
                    "embedding": emb,  # 向量
                    "dimension": len(emb),  # 维度
                }
                for i, emb in enumerate(result["embeddings"])
            ],
            "model": request.model or settings.EMBEDDING_MODEL,  # 使用的模型
            "usage": result.get("usage", {  # 使用量信息
                "total_tokens": sum(len(t) for t in request.texts),
            }),
        }

        # ========== 4. 添加缓存统计 ==========
        if result.get("cache_stats"):
            response["cache_stats"] = result["cache_stats"]

        logger.info(f"批量向量化完成: {len(result['embeddings'])} 个向量")

        return response

    # ========== 5. 异常处理 ==========
    except ValueError as e:
        # 参数错误（包括 Pydantic 验证错误）
        logger.error(f"参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 其他异常
        logger.error(f"批量向量化失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量向量化失败: {str(e)}"
        )


# ============================================================================
# Pydantic 验证器说明
# ============================================================================
# Pydantic 验证器（@validator）：
#   - 在数据进入模型之前执行验证
#   - 可以修改数据（如去除空格）
#   - 验证失败时抛出 ValueError
#
# 验证器参数：
#   - pre=True: 在类型转换之前执行
#   - pre=False: 在类型转换之后执行
#
# 示例：
#   @validator('text', pre=True)
#   def validate_text(cls, v):
#       if not v:
#           raise ValueError("文本不能为空")
#       return v.strip()

# ============================================================================
# 向量化流程说明
# ============================================================================
# 1. 输入验证
#    - Pydantic 验证器验证输入
#    - 过滤空文本
#
# 2. 文本预处理
#    - 去除首尾空格
#    - 转换为统一格式
#
# 3. 模型加载
#    - 加载 Sentence Transformers 模型
#    - 支持多种模型（baai/bge-m3、all-MiniLM-L6-v2 等）
#
# 4. 向量化
#    - 将文本输入模型
#    - 获取向量表示
#
# 5. 缓存
#    - 缓存向量化结果（可选）
#    - 避免重复计算
#
# 6. 返回结果
#    - 返回向量、维度、模型信息

# ============================================================================
# 向量维度说明
# ============================================================================
# 不同模型的向量维度：
#   - baai/bge-m3: 1024 维
#   - all-MiniLM-L6-v2: 384 维
#   - text-embedding-ada-002: 1536 维
#
# 维度越高：
#   - 表达能力越强
#   - 计算成本越高
#   - 存储空间越大

# ============================================================================
# 性能优化建议
# ============================================================================
# 1. 批量处理
#    - 使用 embed_batch 而不是多次调用 embed_single
#    - 批量处理可以利用 GPU 并行计算
#
# 2. 缓存
#    - 缓存常见查询的向量
#    - 使用 Redis 或内存缓存
#
# 3. 模型优化
#    - 使用量化模型（减少内存占用）
#    - 使用 ONNX 加速推理
#
# 4. 异步处理
#    - 使用异步 I/O
#    - 避免阻塞主线程
