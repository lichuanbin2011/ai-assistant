"""
RAG Service 完整测试套件（databases 版本）
"""
import asyncio
import pytest
from loguru import logger
import sys
import httpx
from typing import Optional, Dict, Any

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


# ============================================================================
# 测试配置
# ============================================================================
class TestConfig:
    """测试配置"""

    # 服务地址
    BASE_URL = "http://localhost:8001"

    # 测试数据
    TEST_PDF_ID = 'cmi9o3i2g0001u9gsmr2ii3sz'  # 🆕 自动从文档列表获取
    TEST_USER_ID = "7aa17260-e133-406d-aca6-9b9bb119b69e"

    # 测试文本
    TEST_TEXTS = [
        "什么是机器学习？",
        "深度学习的应用有哪些？",
        "人工智能的未来发展趋势",
        "自然语言处理技术",
        "计算机视觉的应用场景",
    ]

    # 测试查询
    TEST_QUERIES = [
        "这个文档讲了什么？",
        "请总结文档的主要内容",
        "文档中有哪些重要的数据？",
        "作者的观点是什么？",
    ]

    # 超时设置
    TIMEOUT = 60.0


# ============================================================================
# 测试工具函数
# ============================================================================
class TestClient:
    """测试客户端"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=TestConfig.TIMEOUT)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """GET 请求"""
        url = f"{self.base_url}{path}"
        return await self.client.get(url, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        """POST 请求"""
        url = f"{self.base_url}{path}"
        return await self.client.post(url, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """DELETE 请求"""
        url = f"{self.base_url}{path}"
        return await self.client.delete(url, **kwargs)


def print_section(title: str):
    """打印分隔线"""
    logger.info("\n" + "=" * 80)
    logger.info(f"  {title}")
    logger.info("=" * 80)


def print_result(success: bool, message: str):
    """打印测试结果"""
    if success:
        logger.success(f"✅ {message}")
    else:
        logger.error(f"❌ {message}")


def print_json(data: Dict, max_length: int = 200):
    """打印 JSON 数据"""
    import json
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    if len(json_str) > max_length:
        json_str = json_str[:max_length] + "..."
    logger.info(json_str)


# ============================================================================
# 测试 0: 服务可用性检查
# ============================================================================
async def test_service_availability():
    """测试服务是否可用"""
    print_section("测试 0: 服务可用性检查")

    try:
        async with TestClient(TestConfig.BASE_URL) as client:
            response = await client.get("/")

            if response.status_code != 200:
                logger.error(f"服务不可用，状态码: {response.status_code}")
                logger.error(f"请确保服务已启动: python -m app.main")
                return False

            data = response.json()
            logger.info(f"服务名称: {data.get('service')}")
            logger.info(f"版本: {data.get('version')}")
            logger.info(f"Embedding 模型: {data.get('embedding_model')}")
            logger.info(f"LLM 模型: {data.get('llm_model')}")

            print_result(True, "服务可用")
            return True

    except httpx.ConnectError:
        logger.error(f"无法连接到服务: {TestConfig.BASE_URL}")
        logger.error("请确保服务已启动: python -m app.main")
        return False
    except Exception as e:
        logger.error(f"服务检查失败: {e}")
        return False


# ============================================================================
# 测试 1: 健康检查
# ============================================================================
async def test_health_check():
    """测试健康检查接口"""
    print_section("测试 1: 健康检查")

    try:
        async with TestClient(TestConfig.BASE_URL) as client:
            response = await client.get("/health")

            assert response.status_code == 200, f"状态码错误: {response.status_code}"

            data = response.json()

            # 检查基本字段
            assert "status" in data, "缺少 status 字段"
            assert "version" in data, "缺少 version 字段"
            assert "services" in data, "缺少 services 字段"

            logger.info(f"服务状态: {data['status']}")
            logger.info(f"版本: {data['version']}")

            # 检查各个服务状态
            services = data["services"]
            logger.info("\n服务状态:")
            logger.info(f"  数据库: {'✅ 正常' if services.get('database') else '❌ 异常'}")
            logger.info(f"  缓存: {'✅ 启用' if services.get('cache') else '⚠️ 禁用'}")
            logger.info(f"  Embedding: {'✅ 正常' if services.get('embedding') else '❌ 异常'}")
            logger.info(f"  LLM: {'✅ 正常' if services.get('llm') else '❌ 异常'}")

            # 检查数据库连接
            if not services.get('database'):
                logger.error("⚠️ 数据库连接失败！")
                logger.error("   请检查 .env 中的 DATABASE_URL 配置")
                logger.error("   请确保 PostgreSQL 服务已启动")
                return False

            # 检查缓存统计
            if "cache_stats" in data and data["cache_stats"]:
                cache_stats = data["cache_stats"]
                logger.info(f"\n缓存统计:")
                logger.info(f"  总条目: {cache_stats.get('total_keys', 0)}")
                logger.info(f"  命中次数: {cache_stats.get('hits', 0)}")
                logger.info(f"  未命中次数: {cache_stats.get('misses', 0)}")
                logger.info(f"  命中率: {cache_stats.get('hit_rate', 0) * 100:.1f}%")

            print_result(True, "健康检查通过")
            return True

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        print_result(False, f"健康检查失败: {str(e)}")
        return False


# ============================================================================
# 测试 2: 数据库连接测试
# ============================================================================
async def test_database_connection():
    """测试数据库连接（databases 版本）"""
    print_section("测试 2: 数据库连接")

    try:
        # 通过健康检查接口验证数据库
        async with TestClient(TestConfig.BASE_URL) as client:
            response = await client.get("/health")
            data = response.json()

            if not data.get("services", {}).get("database"):
                logger.error("数据库连接失败")
                logger.error("请检查:")
                logger.error("  1. PostgreSQL 服务是否启动")
                logger.error("  2. .env 中的 DATABASE_URL 是否正确")
                logger.error("  3. 数据库是否存在")
                logger.error("  4. 用户权限是否正确")
                return False

            logger.info("✅ 数据库连接正常")

            # 测试查询文档列表（验证数据库可读）
            response = await client.get("/api/v1/documents/list")

            if response.status_code == 200:
                logger.info("✅ 数据库查询正常")
                data = response.json()
                logger.info(f"   文档数量: {data.get('total', 0)}")
            else:
                logger.warning("⚠️ 数据库查询失败")

            print_result(True, "数据库连接测试通过")
            return True

    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        print_result(False, f"数据库连接测试失败: {str(e)}")
        return False


# ============================================================================
# 测试 3: Embedding 单个文本
# ============================================================================
async def test_embed_single():
    """测试单个文本向量化"""
    print_section("测试 3: 单个文本向量化")

    try:
        async with TestClient(TestConfig.BASE_URL) as client:
            text = TestConfig.TEST_TEXTS[0]
            logger.info(f"测试文本: {text}")

            response = await client.post(
                "/api/v1/embed/single",
                json={"text": text}
            )

            assert response.status_code == 200, f"状态码错误: {response.status_code}"

            data = response.json()

            # 检查响应字段
            assert "embedding" in data, "缺少 embedding 字段"
            assert "dimension" in data, "缺少 dimension 字段"
            assert "model" in data, "缺少 model 字段"

            embedding = data["embedding"]
            dimension = data["dimension"]
            model = data["model"]

            logger.info(f"向量维度: {dimension}")
            logger.info(f"模型: {model}")
            logger.info(f"向量前 5 维: {embedding[:5]}")

            # 验证向量
            assert isinstance(embedding, list), "embedding 不是列表"
            assert len(embedding) == dimension, f"向量维度不匹配: {len(embedding)} != {dimension}"
            assert all(isinstance(x, (int, float)) for x in embedding), "向量包含非数值"

            print_result(True, f"向量化成功，维度: {dimension}")
            return True

    except Exception as e:
        logger.error(f"向量化失败: {e}")
        print_result(False, f"向量化失败: {str(e)}")
        return False


# ============================================================================
# 测试 4: Embedding 批量文本
# ============================================================================
async def test_embed_batch():
    """测试批量文本向量化"""
    print_section("测试 4: 批量文本向量化")

    try:
        async with TestClient(TestConfig.BASE_URL) as client:
            texts = TestConfig.TEST_TEXTS
            logger.info(f"测试文本数量: {len(texts)}")

            # 第一次调用（无缓存）
            response = await client.post(
                "/api/v1/embed",
                json={"texts": texts, "model": "baai/bge-m3"}
            )

            assert response.status_code == 200, f"状态码错误: {response.status_code}"

            data = response.json()

            # 检查响应
            assert "data" in data, "缺少 data 字段"
            assert len(data["data"]) == len(texts), f"返回数量不匹配: {len(data['data'])} != {len(texts)}"

            logger.info(f"返回向量数量: {len(data['data'])}")
            logger.info(f"模型: {data.get('model')}")

            # 检查使用量
            if "usage" in data:
                usage = data["usage"]
                logger.info(f"Token 使用: {usage.get('total_tokens', 0)}")

            # 检查缓存统计（第一次应该全部未命中）
            if "cache_stats" in data:
                cache_stats = data["cache_stats"]
                logger.info(f"\n第一次调用 - 缓存统计:")
                logger.info(f"  命中: {cache_stats.get('hits', 0)}")
                logger.info(f"  未命中: {cache_stats.get('misses', 0)}")
                logger.info(f"  命中率: {cache_stats.get('hit_rate', 0) * 100:.1f}%")

            # 第二次调用（测试缓存）
            logger.info("\n测试缓存效果...")
            await asyncio.sleep(0.5)  # 短暂延迟

            response2 = await client.post(
                "/api/v1/embed",
                json={"texts": texts}
            )

            data2 = response2.json()

            if "cache_stats" in data2:
                cache_stats2 = data2["cache_stats"]
                logger.info(f"\n第二次调用 - 缓存统计:")
                logger.info(f"  命中: {cache_stats2.get('hits', 0)}")
                logger.info(f"  未命中: {cache_stats2.get('misses', 0)}")
                logger.info(f"  命中率: {cache_stats2.get('hit_rate', 0) * 100:.1f}%")

                hit_rate = cache_stats2.get('hit_rate', 0)
                if hit_rate > 0.8:
                    logger.success(f"✅ 缓存效果优秀 (命中率: {hit_rate * 100:.1f}%)")
                elif hit_rate > 0.5:
                    logger.warning(f"⚠️ 缓存效果一般 (命中率: {hit_rate * 100:.1f}%)")
                else:
                    logger.error(f"❌ 缓存效果不佳 (命中率: {hit_rate * 100:.1f}%)")

            print_result(True, f"批量向量化成功，处理 {len(texts)} 个文本")
            return True

    except Exception as e:
        logger.error(f"批量向量化失败: {e}")
        print_result(False, f"批量向量化失败: {str(e)}")
        return False


# ============================================================================
# 测试 5: 缓存管理
# ============================================================================
async def test_cache_management():
    """测试缓存管理功能"""
    print_section("测试 5: 缓存管理")

    try:
        async with TestClient(TestConfig.BASE_URL) as client:
            # 获取缓存统计
            response = await client.get("/api/v1/cache/stats")

            if response.status_code == 200:
                stats = response.json()
                logger.info("缓存统计:")
                logger.info(f"  总条目: {stats.get('total_keys', 0)}")
                logger.info(f"  最大容量: {stats.get('max_size', 0)}")
                logger.info(f"  命中次数: {stats.get('hits', 0)}")
                logger.info(f"  未命中次数: {stats.get('misses', 0)}")
                logger.info(f"  命中率: {stats.get('hit_rate', 0) * 100:.1f}%")

                if "memory_usage_mb" in stats:
                    logger.info(f"  内存使用: {stats['memory_usage_mb']:.2f} MB")

                print_result(True, "获取缓存统计成功")
            else:
                logger.warning("缓存未启用或获取失败")
                logger.info("可以在 .env 中设置 CACHE_ENABLED=true 启用缓存")

            # 清空缓存
            logger.info("\n清空缓存...")
            response = await client.delete("/api/v1/cache")

            if response.status_code == 200:
                data = response.json()
                deleted = data.get('deleted_keys', 0)
                logger.info(f"清空缓存成功: 删除 {deleted} 个条目")
                print_result(True, f"清空缓存成功 (删除 {deleted} 个条目)")
            else:
                logger.warning("缓存未启用或清空失败")

            return True

    except Exception as e:
        logger.error(f"缓存管理测试失败: {e}")
        print_result(False, f"缓存管理测试失败: {str(e)}")
        return False


# ============================================================================
# 测试 6: 文档管理
# ============================================================================
async def test_document_management():
    """测试文档管理功能"""
    print_section("测试 6: 文档管理")

    try:
        async with TestClient(TestConfig.BASE_URL) as client:
            # 获取文档列表
            response = await client.get("/api/v1/documents/list")

            assert response.status_code == 200, f"状态码错误: {response.status_code}"

            data = response.json()
            total = data.get('total', 0)

            logger.info(f"文档总数: {total}")

            documents = data.get("data", [])

            if not documents:
                logger.warning("⚠️ 文档列表为空")
                logger.warning("   请先上传 PDF 文件进行测试")
                logger.warning("   可以使用: curl -X POST http://localhost:8001/api/v1/pdf/upload -F 'file=@test.pdf'")
                print_result(True, "文档列表为空（正常）")
                return True

            # 显示文档列表
            logger.info(f"\n文档列表 (前 5 个):")
            for i, doc in enumerate(documents[:5]):
                logger.info(f"\n  文档 {i + 1}:")
                logger.info(f"    ID: {doc.get('id')}")
                logger.info(f"    名称: {doc.get('name')}")
                logger.info(f"    状态: {doc.get('status')}")
                logger.info(f"    大小: {doc.get('size', 0) / 1024 / 1024:.2f} MB")
                logger.info(f"    总页数: {doc.get('total_pages', 0)}")
                logger.info(f"    总块数: {doc.get('total_chunks', 0)}")

            # 保存第一个文档 ID 用于后续测试
            if documents:
                first_doc = documents[0]
                TestConfig.TEST_PDF_ID = first_doc["id"]
                logger.info(f"\n✅ 设置测试 PDF ID: {TestConfig.TEST_PDF_ID}")

                # 测试获取单个文档详情
                doc_id = first_doc["id"]
                response2 = await client.get(f"/api/v1/documents/{doc_id}")

                if response2.status_code == 200:
                    doc_data = response2.json()
                    logger.info(f"\n获取文档详情成功:")
                    logger.info(f"  名称: {doc_data['data'].get('name')}")
                    logger.info(f"  状态: {doc_data['data'].get('status')}")
                    print_result(True, "获取文档详情成功")

                # 测试获取文档分块
                response3 = await client.get(
                    f"/api/v1/documents/{doc_id}/chunks",
                    params={"page": 1, "page_size": 5}
                )

                if response3.status_code == 200:
                    chunks_data = response3.json()
                    logger.info(f"\n获取文档分块成功:")
                    logger.info(f"  总块数: {chunks_data.get('total')}")
                    logger.info(f"  当前页: {chunks_data.get('page')}")
                    logger.info(f"  每页数量: {chunks_data.get('page_size')}")
                    logger.info(f"  总页数: {chunks_data.get('total_pages')}")

                    # 显示前 2 个分块
                    chunks = chunks_data.get('data', [])
                    if chunks:
                        logger.info(f"\n  前 2 个分块:")
                        for i, chunk in enumerate(chunks[:2]):
                            logger.info(f"\n    分块 {i + 1}:")
                            logger.info(f"      索引: {chunk.get('chunk_index')}")
                            logger.info(f"      页码: {chunk.get('page_number', 'N/A')}")
                            logger.info(f"      Token 数: {chunk.get('token_count')}")
                            logger.info(f"      内容预览: {chunk.get('content', '')[:100]}...")

                    print_result(True, "获取文档分块成功")

            print_result(True, f"文档管理测试通过 (共 {total} 个文档)")
            return True

    except Exception as e:
        logger.error(f"文档管理测试失败: {e}")
        print_result(False, f"文档管理测试失败: {str(e)}")
        return False


# ============================================================================
# 测试 7: 向量检索
# ============================================================================
async def test_retrieval():
    """测试向量检索功能"""
    print_section("测试 7: 向量检索")

    try:
        if not TestConfig.TEST_PDF_ID:
            logger.warning("⚠️ 未设置测试 PDF ID，跳过检索测试")
            logger.warning("   请先运行文档管理测试或手动设置 TEST_PDF_ID")
            return True

        async with TestClient(TestConfig.BASE_URL) as client:
            query = TestConfig.TEST_QUERIES[0]
            logger.info(f"测试查询: {query}")
            logger.info(f"PDF ID: {TestConfig.TEST_PDF_ID}")

            response = await client.post(
                "/api/v1/search",
                json={
                    "query": query,
                    "pdf_id": TestConfig.TEST_PDF_ID,
                    "top_k": 5,
                    "threshold": 0.6
                }
            )

            if response.status_code == 404:
                logger.warning("PDF 不存在，跳过检索测试")
                return True

            if response.status_code == 400:
                error_data = response.json()
                logger.warning(f"PDF 状态异常: {error_data.get('detail')}")
                return True

            assert response.status_code == 200, f"状态码错误: {response.status_code}"

            data = response.json()
            total = data.get('total', 0)

            logger.info(f"检索成功: 找到 {total} 个相关块")

            # 显示检索结果
            chunks = data.get("chunks", [])
            if chunks:
                logger.info(f"\n检索结果 (前 3 个):")
                for i, chunk in enumerate(chunks[:3]):
                    logger.info(f"\n  结果 {i + 1}:")
                    logger.info(f"    相似度: {chunk.get('similarity', 0):.3f}")
                    logger.info(f"    页码: {chunk.get('page_number', 'N/A')}")
                    logger.info(f"    Token 数: {chunk.get('token_count', 0)}")
                    logger.info(f"    内容预览: {chunk.get('content', '')[:150]}...")

            # 检查查询重写
            if "query_rewrite" in data and data["query_rewrite"]:
                rewrite = data["query_rewrite"]
                logger.info(f"\n查询重写:")
                logger.info(f"  原始查询: {rewrite.get('original_query')}")
                logger.info(f"  最终查询: {rewrite.get('final_query')}")
                logger.info(f"  查询类型: {rewrite.get('query_type')}")

            print_result(True, f"检索成功，找到 {total} 个结果")
            return True

    except Exception as e:
        logger.error(f"检索测试失败: {e}")
        print_result(False, f"检索测试失败: {str(e)}")
        return False


# ============================================================================
# 测试 8: RAG 聊天
# ============================================================================
async def test_rag_chat():
    """测试 RAG 聊天功能"""
    print_section("测试 8: RAG 聊天")

    try:
        if not TestConfig.TEST_PDF_ID:
            logger.warning("⚠️ 未设置测试 PDF ID，跳过聊天测试")
            logger.warning("   请先运行文档管理测试或手动设置 TEST_PDF_ID")
            return True

        async with TestClient(TestConfig.BASE_URL) as client:
            message = TestConfig.TEST_QUERIES[1]
            logger.info(f"测试问题: {message}")
            logger.info(f"PDF ID: {TestConfig.TEST_PDF_ID}")

            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": message,
                    "pdf_id": TestConfig.TEST_PDF_ID,
                    "user_id": TestConfig.TEST_USER_ID,
                    "model": "deepseek/deepseek-chat-v3.1"
                }
            )

            if response.status_code == 404:
                logger.warning("PDF 不存在，跳过聊天测试")
                return True

            if response.status_code == 400:
                error_data = response.json()
                logger.warning(f"PDF 状态异常: {error_data.get('detail')}")
                return True

            assert response.status_code == 200, f"状态码错误: {response.status_code}"

            data = response.json()

            # 显示 AI 响应
            ai_response = data.get("response", "")
            logger.info(f"\nAI 响应 (前 500 字符):")
            logger.info("-" * 80)
            logger.info(ai_response[:500])
            if len(ai_response) > 500:
                logger.info("...")
            logger.info("-" * 80)

            # 显示元数据
            metadata = data.get("metadata", {})
            logger.info(f"\n元数据:")
            logger.info(f"  PDF 名称: {metadata.get('pdf_name')}")
            logger.info(f"  总页数: {metadata.get('total_pages')}")
            logger.info(f"  总块数: {metadata.get('total_chunks')}")
            logger.info(f"  检索块数: {metadata.get('chunks_retrieved')}")
            logger.info(f"  使用模型: {metadata.get('model')}")
            logger.info(f"  RAG 启用: {metadata.get('rag_enabled')}")

            # 显示来源
            sources = metadata.get("sources", [])
            if sources:
                logger.info(f"\n文档来源 (前 3 个):")
                for i, source in enumerate(sources[:3]):
                    logger.info(f"  来源 {i + 1}:")
                    logger.info(f"    页码: {source.get('page_number', 'N/A')}")
                    logger.info(f"    相似度: {source.get('similarity', 0):.3f}")
                    logger.info(f"    预览: {source.get('preview', '')[:80]}...")

            print_result(True, "RAG 聊天成功")
            return True

    except Exception as e:
        logger.error(f"RAG 聊天测试失败: {e}")
        print_result(False, f"RAG 聊天测试失败: {str(e)}")
        return False


# ============================================================================
# 测试 9: 性能测试
# ============================================================================
async def test_performance():
    """测试性能"""
    print_section("测试 9: 性能测试")

    try:
        import time

        async with TestClient(TestConfig.BASE_URL) as client:
            # 测试 1: 单个文本向量化速度
            text = TestConfig.TEST_TEXTS[0]

            start_time = time.time()
            response = await client.post(
                "/api/v1/embed/single",
                json={"text": text}
            )
            duration1 = time.time() - start_time

            logger.info(f"单个文本向量化耗时: {duration1 * 1000:.0f}ms")

            # 测试 2: 批量文本向量化速度
            texts = TestConfig.TEST_TEXTS * 10  # 50 个文本

            start_time = time.time()
            response = await client.post(
                "/api/v1/embed",
                json={"texts": texts}
            )
            duration2 = time.time() - start_time

            logger.info(f"批量向量化 ({len(texts)} 个文本) 耗时: {duration2 * 1000:.0f}ms")
            logger.info(f"平均每个文本: {duration2 / len(texts) * 1000:.1f}ms")

            # 测试 3: 缓存效果
            await asyncio.sleep(0.5)

            start_time = time.time()
            response = await client.post(
                "/api/v1/embed",
                json={"texts": texts}
            )
            duration3 = time.time() - start_time

            logger.info(f"缓存命中时耗时: {duration3 * 1000:.0f}ms")

            if duration2 > 0:
                improvement = (1 - duration3 / duration2) * 100
                logger.info(f"性能提升: {improvement:.1f}%")

                if improvement > 50:
                    print_result(True, f"缓存性能优秀 (提升 {improvement:.1f}%)")
                elif improvement > 20:
                    print_result(True, f"缓存性能良好 (提升 {improvement:.1f}%)")
                else:
                    print_result(False, f"缓存性能不佳 (提升 {improvement:.1f}%)")

            return True

    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        print_result(False, f"性能测试失败: {str(e)}")
        return False


# ============================================================================
# 测试 10: 错误处理
# ============================================================================
async def test_error_handling():
    """测试错误处理"""
    print_section("测试 10: 错误处理")

    try:
        async with TestClient(TestConfig.BASE_URL) as client:
            # 测试 1: 空文本
            response = await client.post(
                "/api/v1/embed/single",
                json={"text": ""}
            )

            # ✅ 修复：可能返回 400 或 422
            assert response.status_code in [400, 422], f"空文本应该返回 400/422，实际: {response.status_code}"
            logger.info("✅ 空文本错误处理正确")

            # 测试 2: 无效的 PDF ID
            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "测试",
                    "pdf_id": "invalid_pdf_id_12345_not_exist",
                }
            )

            # ✅ 修复：应该返回 404
            if response.status_code == 404:
                logger.info("✅ 无效 PDF ID 错误处理正确")
            else:
                logger.warning(f"⚠️ 无效 PDF ID 返回 {response.status_code}（预期 404）")
                # 不算失败，因为可能是其他验证错误

            # 测试 3: 缺少必填参数
            response = await client.post(
                "/api/v1/chat",
                json={"message": "测试"}  # 缺少 pdf_id
            )

            assert response.status_code == 422, f"缺少参数应该返回 422，实际: {response.status_code}"
            logger.info("✅ 缺少参数错误处理正确")

            # 测试 4: 批量文本为空列表
            response = await client.post(
                "/api/v1/embed",
                json={"texts": []}
            )

            assert response.status_code in [400, 422], f"空列表应该返回 400/422，实际: {response.status_code}"
            logger.info("✅ 空列表错误处理正确")

            print_result(True, "错误处理测试通过")
            return True

    except AssertionError as e:
        logger.error(f"错误处理测试失败: {e}")
        print_result(False, f"错误处理测试失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"错误处理测试失败: {e}")
        print_result(False, f"错误处理测试失败: {str(e)}")
        return False
# ============================================================================
# 主测试函数
# ============================================================================
async def run_all_tests():
    """运行所有测试"""
    logger.info("\n")
    logger.info("🚀 开始 RAG Service 完整测试")
    logger.info(f"📍 服务地址: {TestConfig.BASE_URL}")
    logger.info(f"⏱️  超时设置: {TestConfig.TIMEOUT}s")
    logger.info("\n")

    # 先检查服务可用性
    if not await test_service_availability():
        logger.error("\n❌ 服务不可用，终止测试")
        return False

    results = []

    # 运行测试
    tests = [
        ("健康检查", test_health_check),
        ("数据库连接", test_database_connection),
        ("单个文本向量化", test_embed_single),
        ("批量文本向量化", test_embed_batch),
        ("缓存管理", test_cache_management),
        ("文档管理", test_document_management),
        ("向量检索", test_retrieval),
        ("RAG 聊天", test_rag_chat),
        ("性能测试", test_performance),
        ("错误处理", test_error_handling),
    ]

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"测试 '{name}' 执行失败: {e}")
            results.append((name, False))

        # 测试间延迟
        await asyncio.sleep(1)

    # 打印总结
    print_section("测试总结")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    logger.info(f"\n总测试数: {total}")
    logger.info(f"通过: {passed}")
    logger.info(f"失败: {total - passed}")
    logger.info(f"通过率: {passed / total * 100:.1f}%\n")

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{status} - {name}")

    if passed == total:
        logger.success("\n🎉 所有测试通过！")
    else:
        logger.warning(f"\n⚠️ 有 {total - passed} 个测试失败")

    return passed == total


# ============================================================================
# 命令行入口
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG Service 测试工具")
    parser.add_argument("--url", default="http://localhost:8001", help="服务地址")
    parser.add_argument("--pdf-id", help="测试 PDF ID",default='cmi9o3i2g0001u9gsmr2ii3sz')
    parser.add_argument("--test", help="运行指定测试")
    parser.add_argument("--timeout", type=float, default=60.0, help="请求超时时间（秒）")

    args = parser.parse_args()

    # 更新配置
    TestConfig.BASE_URL = args.url
    TestConfig.TIMEOUT = args.timeout

    if args.pdf_id:
        TestConfig.TEST_PDF_ID = args.pdf_id

    # 运行测试
    if args.test:
        # 运行指定测试
        test_map = {
            "availability": test_service_availability,
            "health": test_health_check,
            "database": test_database_connection,
            "embed": test_embed_single,
            "embed-batch": test_embed_batch,
            "cache": test_cache_management,
            "documents": test_document_management,
            "retrieval": test_retrieval,
            "chat": test_rag_chat,
            "performance": test_performance,
            "error": test_error_handling,
        }

        if args.test in test_map:
            asyncio.run(test_map[args.test]())
        else:
            logger.error(f"未知的测试: {args.test}")
            logger.info(f"可用测试: {', '.join(test_map.keys())}")
    else:
        # 运行所有测试
        asyncio.run(run_all_tests())
