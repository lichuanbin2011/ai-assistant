"""
============================================================================
Embedding 核心服务模块
============================================================================

文件位置：
  rag-service/app/services/embedding.py

文件作用：
  负责文本向量化（Embedding），将文本转换为高维向量用于语义相似度计算

主要功能：
  1. 单文本向量化 - 将单个文本转换为向量
  2. 批量向量化 - 高效处理大量文本的向量化
  3. 缓存管理 - 缓存已计算的向量，避免重复计算
  4. Token 计数 - 计算文本的 Token 数量，用于成本估算
  5. 错误处理 - 自动重试和降级处理

技术栈：
  - httpx（异步 HTTP 客户端）
  - tiktoken（Token 计数工具）
  - OpenRouter API（Embedding API 提供商）
  - asyncio（异步编程）

依赖文件：
  - app/core/config.py（配置管理）
  - app/core/cache.py（缓存管理）

API 要求：
  - OpenRouter API Key
  - 支持的 Embedding 模型（如 baai/bge-m3）

使用场景：
  1. PDF 文档处理 - 将文档块转换为向量存储到数据库
  2. 用户查询处理 - 将用户问题转换为向量用于检索
  3. 相似度计算 - 通过向量相似度找到相关文档

使用示例：
    ```python
    from app.services.embedding import get_embedding_service
    
    service = get_embedding_service()
    
    # 单个文本向量化
    embedding = await service.embed_single("什么是机器学习？")
    # 返回: [0.1, 0.2, ..., 0.5]（1024 维向量）
    
    # 批量文本向量化
    result = await service.embed_batch([
        "机器学习是人工智能的一个分支",
        "深度学习是机器学习的一个子领域"
    ])
    # 返回:
    # {
    #     "embeddings": [[...], [...]],
    #     "cache_stats": {"hits": 0, "misses": 2, "hit_rate": 0.0},
    #     "usage": {"prompt_tokens": 50, "total_tokens": 50}
    # }
    
    # Token 计数
    tokens = service.count_tokens("你好世界")
    # 返回: 约 3
    ```

性能优化：
  - 缓存机制：避免重复计算相同文本
  - 批量处理：减少 API 调用次数
  - 自动重试：失败时自动降级为单个处理
  - 限流控制：避免触发 API 限流

============================================================================
"""
import httpx  # HTTP 客户端，用于调用 API
import asyncio  # 异步编程支持
import tiktoken  # OpenAI 的 Token 计数工具
from typing import List, Dict, Any, Optional
from loguru import logger  # 日志记录

from app.core.config import get_settings  # 获取配置
from app.core.cache import get_cache  # 获取缓存实例


class EmbeddingService:
    """
    Embedding 服务类
    
    职责：
        - 文本向量化（单个/批量）
        - 缓存管理
        - Token 计数
        - API 调用和错误处理
    
    属性：
        settings: 配置对象
        cache: 缓存实例（可选）
        tokenizer: Token 计数器（可选）
    """

    def __init__(self):
        """
        初始化 Embedding 服务
        
        工作流程：
            1. 加载配置（API Key、模型名称等）
            2. 初始化缓存（如果启用）
            3. 初始化 Token 计数器（用于成本估算）
            4. 记录初始化信息
        """
        # 加载配置
        self.settings = get_settings()
        
        # 初始化缓存（如果启用）
        # 缓存用于避免重复计算相同文本的向量，提高性能
        self.cache = get_cache(
            max_size=self.settings.CACHE_MAX_SIZE,  # 最大缓存条目数
            ttl_seconds=self.settings.CACHE_TTL_SECONDS  # 缓存过期时间（秒）
        ) if self.settings.CACHE_ENABLED else None

        # 初始化 Token 计数器
        # tiktoken 是 OpenAI 的官方 Token 计数工具，用于精确计算 Token 数量
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception as e:
            logger.warning(f"Tiktoken 初始化失败: {e}，使用估算方法")
            self.tokenizer = None  # 降级为估算方法

        # 记录初始化信息
        logger.info(f"Embedding Service 初始化完成")
        logger.info(f"  - 模型: {self.settings.EMBEDDING_MODEL}")
        logger.info(f"  - 缓存: {'启用' if self.cache else '禁用'}")

    def count_tokens(self, text: str) -> int:
        """
        计算文本的 Token 数量
        
        Token 说明：
            - Token 是文本的最小单位（类似"词"）
            - 1 个 Token ≈ 4 个英文字符 ≈ 1.5 个中文字符
            - 用于计算 API 使用量和成本
            - 例如："你好世界" ≈ 3 个 Token
        
        计算方法：
            1. 优先使用 tiktoken 精确计数
            2. 失败时降级为估算方法（字符数 / 4）
        
        Args:
            text: 文本内容
        
        Returns:
            Token 数量（整数）
        
        示例：
            count_tokens("Hello World")  # 返回: 2
            count_tokens("你好世界")      # 返回: 约 3
        """
        # 空文本返回 0
        if not text:
            return 0

        # 使用 tiktoken 精确计数
        if self.tokenizer:
            try:
                tokens = self.tokenizer.encode(text)  # 编码为 Token 列表
                return len(tokens)  # 返回 Token 数量
            except Exception as e:
                logger.error(f"Token 计数失败: {e}")

        # 降级：使用估算方法（1 token ≈ 4 字符）
        return len(text) // 4

    async def embed_single(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        单个文本向量化
        
        功能说明：
            将单个文本转换为高维向量（通常是 1024 维或 768 维）
            向量可用于计算文本之间的语义相似度
        
        工作流程：
            1. 验证文本（不能为空）
            2. 检查缓存（如果已计算过，直接返回）
            3. 调用 OpenRouter API 进行向量化
            4. 写入缓存（供下次使用）
            5. 返回向量
        
        Args:
            text: 文本内容（必填）
            model: 模型名称（可选，默认使用配置中的模型）
        
        Returns:
            向量列表（浮点数列表，长度取决于模型）
            例如：[0.1, 0.2, ..., 0.5]（1024 维）
        
        Raises:
            ValueError: 文本为空或 API 调用失败
        
        示例：
            embedding = await embed_single("什么是机器学习？")
            # 返回: [0.1, 0.2, ..., 0.5]（1024 维向量）
            
            # 计算相似度
            similarity = cosine_similarity(embedding1, embedding2)
        """
        # ========== 1. 验证文本 ==========
        if not text or not text.strip():
            raise ValueError("文本不能为空")

        # 使用指定模型或默认模型
        model = model or self.settings.EMBEDDING_MODEL

        # ========== 2. 检查缓存 ==========
        if self.cache:
            cached = self.cache.get(text, model)  # 从缓存获取
            if cached is not None:
                logger.debug(f"缓存命中: {text[:50]}...")  # 记录缓存命中
                return cached

        # ========== 3. 调用 API ==========
        logger.debug(f"调用 API: {text[:50]}... (长度: {len(text)})")

        start_time = asyncio.get_event_loop().time()  # 记录开始时间

        async with httpx.AsyncClient() as client:  # 创建异步 HTTP 客户端
            try:
                # 发送 POST 请求到 OpenRouter API
                response = await client.post(
                    f"{self.settings.OPENROUTER_BASE_URL}/embeddings",  # API 端点
                    headers={
                        "Authorization": f"Bearer {self.settings.OPENROUTER_API_KEY}",  # API 密钥
                        "Content-Type": "application/json",
                        "HTTP-Referer": self.settings.APP_URL,  # 应用 URL（用于统计）
                        "X-Title": self.settings.APP_NAME,  # 应用名称（用于统计）
                    },
                    json={
                        "model": model,  # 模型名称
                        "input": text,  # 输入文本
                    },
                    timeout=30.0,  # 超时时间 30 秒
                )

                response.raise_for_status()  # 检查 HTTP 状态码（4xx/5xx 会抛出异常）
                data = response.json()  # 解析 JSON 响应

                # ========== 4. 验证返回格式 ==========
                # API 返回格式：{"data": [{"embedding": [...]}]}
                if not data.get("data") or not isinstance(data["data"], list):
                    raise ValueError(f"API 返回格式错误: {data}")

                if not data["data"][0].get("embedding"):
                    raise ValueError("API 返回缺少 embedding 字段")

                embedding = data["data"][0]["embedding"]  # 提取向量

                # ========== 5. 写入缓存 ==========
                if self.cache:
                    self.cache.set(text, model, embedding)

                # 记录耗时和维度
                duration = asyncio.get_event_loop().time() - start_time
                logger.debug(f"向量化完成: 耗时 {duration:.2f}s, 维度 {len(embedding)}")

                return embedding

            except httpx.HTTPStatusError as e:
                # HTTP 错误（如 401 未授权, 429 限流, 500 服务器错误）
                logger.error(f"API 错误: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"API 错误 ({e.response.status_code}): {e.response.text}")
            except httpx.RequestError as e:
                # 网络错误（如连接超时、DNS 解析失败）
                logger.error(f"网络错误: {e}")
                raise ValueError(f"网络错误: {str(e)}")

    async def embed_batch(
            self,
            texts: List[str],
            model: Optional[str] = None,
            show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        批量文本向量化
        
        功能说明：
            高效处理大量文本的向量化，相比单个处理有以下优势：
            - 减少 API 调用次数（批量请求）
            - 利用缓存避免重复计算
            - 失败时自动重试
            - 提供详细的统计信息
        
        工作流程：
            1. 验证输入（空列表直接返回）
            2. 分批处理（每批 BATCH_SIZE 个文本，避免单次请求过大）
            3. 检查缓存（已缓存的直接使用，未缓存的调用 API）
            4. 批量调用 API（将未缓存的文本一次性发送）
            5. 失败时逐个重试（避免整个批次失败）
            6. 返回结果和统计信息
        
        性能优化：
            - 缓存机制：避免重复计算
            - 批量请求：减少网络开销
            - 并发控制：避免触发 API 限流
            - 自动重试：提高成功率
        
        Args:
            texts: 文本列表（必填）
            model: 模型名称（可选，默认使用配置中的模型）
            show_progress: 是否显示进度（默认 True）
        
        Returns:
            字典，包含：
                - embeddings: 向量列表（与输入文本顺序一致）
                - cache_stats: 缓存统计
                    - hits: 缓存命中次数
                    - misses: 缓存未命中次数
                    - hit_rate: 缓存命中率（0.0-1.0）
                - usage: 使用量统计
                    - prompt_tokens: 输入 Token 数量
                    - total_tokens: 总 Token 数量
        
        示例：
            result = await embed_batch([
                "机器学习是人工智能的一个分支",
                "深度学习是机器学习的一个子领域"
            ])
            
            # 返回:
            # {
            #     "embeddings": [
            #         [0.1, 0.2, ..., 0.5],  # 第一个文本的向量
            #         [0.3, 0.4, ..., 0.6]   # 第二个文本的向量
            #     ],
            #     "cache_stats": {
            #         "hits": 0,       # 缓存命中 0 次
            #         "misses": 2,     # 缓存未命中 2 次
            #         "hit_rate": 0.0  # 命中率 0%
            #     },
            #     "usage": {
            #         "prompt_tokens": 50,   # 输入 50 个 Token
            #         "total_tokens": 50     # 总共 50 个 Token
            #     }
            # }
        """
        # ========== 1. 验证输入 ==========
        if not texts:
            return {
                "embeddings": [],
                "cache_stats": {"hits": 0, "misses": 0},
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            }

        model = model or self.settings.EMBEDDING_MODEL

        # 记录批量处理信息
        logger.info(f"批量向量化开始: {len(texts)} 个文本")
        logger.info(f"  - 模型: {model}")
        logger.info(f"  - 批次大小: {self.settings.BATCH_SIZE}")

        start_time = asyncio.get_event_loop().time()  # 记录开始时间

        # 初始化统计变量
        results = []  # 存储结果（索引, 向量）
        cache_hits = 0  # 缓存命中次数
        cache_misses = 0  # 缓存未命中次数
        total_tokens = 0  # 总 Token 数量

        # ========== 2. 分批处理 ==========
        batch_size = self.settings.BATCH_SIZE  # 每批处理的文本数量（如 10）
        total_batches = (len(texts) + batch_size - 1) // batch_size  # 总批次数（向上取整）

        # 遍历每个批次
        for batch_idx in range(0, len(texts), batch_size):
            batch = texts[batch_idx:batch_idx + batch_size]  # 当前批次的文本
            batch_num = batch_idx // batch_size + 1  # 当前批次编号（从 1 开始）

            if show_progress:
                logger.info(f"处理批次 {batch_num}/{total_batches} ({len(batch)} 个文本)")

            # ========== 3. 检查缓存 ==========
            batch_results = []  # 当前批次的结果
            uncached_texts = []  # 未缓存的文本
            uncached_indices = []  # 未缓存文本的原始索引

            for i, text in enumerate(batch):
                if self.cache:
                    cached = self.cache.get(text, model)  # 从缓存获取
                    if cached is not None:
                        # 缓存命中，直接使用
                        batch_results.append((batch_idx + i, cached))
                        cache_hits += 1
                        continue

                # 未缓存，添加到待处理列表
                uncached_texts.append(text)
                uncached_indices.append(batch_idx + i)
                cache_misses += 1

            # ========== 4. 批量调用 API（未缓存的） ==========
            if uncached_texts:
                try:
                    async with httpx.AsyncClient() as client:
                        # 发送批量请求
                        response = await client.post(
                            f"{self.settings.OPENROUTER_BASE_URL}/embeddings",
                            headers={
                                "Authorization": f"Bearer {self.settings.OPENROUTER_API_KEY}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": self.settings.APP_URL,
                                "X-Title": self.settings.APP_NAME,
                            },
                            json={
                                "model": model,
                                "input": uncached_texts,  # 批量输入（列表）
                            },
                            timeout=60.0,  # 批量请求超时时间更长
                        )

                        response.raise_for_status()
                        data = response.json()

                        # 验证返回数据
                        if not data.get("data") or len(data["data"]) != len(uncached_texts):
                            raise ValueError(
                                f"返回数量不匹配: 期望 {len(uncached_texts)}, 实际 {len(data.get('data', []))}"
                            )

                        # 提取 embeddings 并写入缓存
                        for text, emb_data, idx in zip(uncached_texts, data["data"], uncached_indices):
                            embedding = emb_data["embedding"]  # 提取向量
                            batch_results.append((idx, embedding))  # 添加到结果

                            if self.cache:
                                self.cache.set(text, model, embedding)  # 写入缓存

                        # 累计 Token 使用量
                        if data.get("usage"):
                            total_tokens += data["usage"].get("total_tokens", 0)

                        logger.debug(f"批次 {batch_num} 完成")

                except Exception as e:
                    # ========== 5. 失败时逐个重试 ==========
                    logger.error(f"批次 {batch_num} 失败: {e}")

                    # 逐个重试，避免整个批次失败
                    logger.info(f"逐个重试批次 {batch_num}...")
                    for text, idx in zip(uncached_texts, uncached_indices):
                        try:
                            embedding = await self.embed_single(text, model)  # 单个重试
                            batch_results.append((idx, embedding))

                            # 避免频繁请求（限流）
                            await asyncio.sleep(0.3)
                        except Exception as retry_error:
                            logger.error(f"文本 {idx} 重试失败: {retry_error}")
                            # 返回零向量（避免整个批次失败）
                            batch_results.append((idx, [0.0] * 1024))

            results.extend(batch_results)

            # 批次间延迟，避免触发 API 限流
            if batch_idx + batch_size < len(texts):
                await asyncio.sleep(0.5)

        # ========== 6. 按原始顺序排序 ==========
        results.sort(key=lambda x: x[0])  # 按索引排序
        embeddings = [emb for _, emb in results]  # 提取向量

        duration = asyncio.get_event_loop().time() - start_time

        # 记录统计信息
        logger.info(f"批量向量化完成: 耗时 {duration:.2f}s")
        logger.info(f"  - 缓存命中: {cache_hits}")
        logger.info(f"  - 缓存未命中: {cache_misses}")
        logger.info(f"  - 总 Tokens: {total_tokens}")

        return {
            "embeddings": embeddings,
            "cache_stats": {
                "hits": cache_hits,
                "misses": cache_misses,
                "hit_rate": cache_hits / len(texts) if len(texts) > 0 else 0,
            },
            "usage": {
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens,
            },
        }


# ============================================================================
# 全局服务实例（单例模式）
# ============================================================================

_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取 Embedding 服务实例（单例模式）
    
    单例模式说明：
        - 全局只创建一个 EmbeddingService 实例
        - 避免重复初始化（节省资源）
        - 所有地方共享同一个缓存
    
    Returns:
        EmbeddingService 实例
    
    示例：
        service = get_embedding_service()
        embedding = await service.embed_single("你好")
    """
    global _service_instance

    if _service_instance is None:
        _service_instance = EmbeddingService()

    return _service_instance
