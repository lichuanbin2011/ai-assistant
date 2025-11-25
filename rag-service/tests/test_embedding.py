"""
Embedding Service 单元测试
"""
import pytest
from app.services.embedding import EmbeddingService


@pytest.mark.asyncio
async def test_embed_single():
    """测试单个文本向量化"""
    service = EmbeddingService()

    text = "什么是机器学习？"
    embedding = await service.embed_single(text)

    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_embed_batch():
    """测试批量向量化"""
    service = EmbeddingService()

    texts = [
        "什么是机器学习？",
        "深度学习的应用",
        "人工智能的未来",
    ]

    result = await service.embed_batch(texts, show_progress=False)

    assert len(result["embeddings"]) == len(texts)
    assert result["cache_stats"]["hits"] + result["cache_stats"]["misses"] == len(texts)


@pytest.mark.asyncio
async def test_cache():
    """测试缓存功能"""
    service = EmbeddingService()

    text = "测试缓存"

    # 第一次调用（缓存未命中）
    result1 = await service.embed_batch([text], show_progress=False)
    assert result1["cache_stats"]["misses"] == 1

    # 第二次调用（缓存命中）
    result2 = await service.embed_batch([text], show_progress=False)
    assert result2["cache_stats"]["hits"] == 1
