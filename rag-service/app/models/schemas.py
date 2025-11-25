"""
============================================================================
Pydantic 数据模型模块
============================================================================

文件位置：
  rag-service/app/schemas.py

文件作用：
  定义 API 请求和响应的数据模型，用于数据验证和序列化

主要功能：
  1. 数据验证 - 自动验证请求数据的格式和类型
  2. 数据序列化 - 将 Python 对象转换为 JSON
  3. 数据文档 - 自动生成 API 文档
  4. 类型提示 - 提供 IDE 自动补全和类型检查

模型分类：
  - Embedding 相关：向量化请求和响应
  - RAG 相关：聊天、检索请求和响应
  - 系统相关：健康检查、错误响应

技术栈：
  - Pydantic（数据验证）
  - FastAPI（自动集成）

依赖文件：
  无（独立模块）

使用示例：
    ```python
    from app.schemas import ChatRequest, ChatResponse
    
    # 创建请求对象
    request = ChatRequest(
        message="什么是机器学习？",
        pdf_id="123"
    )
    
    # 验证数据
    print(request.message)  # "什么是机器学习？"
    
    # 转换为 JSON
    json_data = request.dict()
    ```

============================================================================
"""
"""
Pydantic 数据模型 - 定义 API 的请求和响应格式
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================================================
# Embedding 相关模型
# ============================================================================

class EmbedRequest(BaseModel):
    """
    向量化请求
    
    示例：
        {
            "texts": ["你好", "世界"],
            "model": "baai/bge-m3",
            "encoding_format": "float"
        }
    """
    texts: List[str] = Field(..., min_items=1, max_items=100, description="文本列表")
    # 必填，1-100 个文本
    
    model: Optional[str] = Field(None, description="Embedding 模型")
    # 可选，默认使用配置中的模型
    
    encoding_format: Optional[str] = Field("float", description="编码格式: float 或 base64")
    # 可选，默认 float

    @validator('texts')
    def validate_texts(cls, v):
        """验证文本列表 - 不能为空，不能只包含空格"""
        if not v:
            raise ValueError("文本列表不能为空")

        for text in v:
            if not text or not text.strip():
                raise ValueError("文本内容不能为空")

        return v


class EmbeddingData(BaseModel):
    """
    单个 Embedding 数据
    
    示例：
        {
            "object": "embedding",
            "embedding": [0.1, 0.2, ...],
            "index": 0
        }
    """
    object: str = "embedding"
    # 固定值，兼容 OpenAI 格式
    
    embedding: List[float]
    # 向量数据，长度取决于模型（如 1024 维）
    
    index: int
    # 文本在请求列表中的索引


class UsageInfo(BaseModel):
    """
    使用量信息
    
    示例：
        {
            "prompt_tokens": 100,
            "total_tokens": 100,
            "cost": 0.001
        }
    """
    prompt_tokens: int
    # 输入 Token 数量
    
    total_tokens: int
    # 总 Token 数量
    
    cost: Optional[float] = None
    # 成本（美元），可选


class CacheStats(BaseModel):
    """
    缓存统计
    
    示例：
        {
            "hits": 8,
            "misses": 2,
            "hit_rate": 0.8
        }
    """
    hits: int = 0
    # 缓存命中次数
    
    misses: int = 0
    # 缓存未命中次数
    
    hit_rate: Optional[float] = None
    # 缓存命中率（0.0-1.0）


class EmbedResponse(BaseModel):
    """
    向量化响应
    
    示例：
        {
            "object": "list",
            "data": [...],
            "model": "baai/bge-m3",
            "usage": {...},
            "cache_stats": {...}
        }
    """
    object: str = "list"
    # 固定值，兼容 OpenAI 格式
    
    data: List[EmbeddingData]
    # 向量数据列表
    
    model: str
    # 使用的模型名称
    
    usage: UsageInfo
    # 使用量信息
    
    cache_stats: Optional[CacheStats] = None
    # 缓存统计，可选


# ============================================================================
# RAG 相关模型
# ============================================================================

class ChatRequest(BaseModel):
    """
    RAG 聊天请求
    
    示例：
        {
            "message": "什么是机器学习？",
            "pdf_id": "123",
            "model": "deepseek/deepseek-chat-v3.1",
            "user_id": "user_456"
        }
    """
    message: str = Field(..., min_length=1, max_length=5000)
    # 用户消息，1-5000 字符
    
    pdf_id: str = Field(..., description="PDF 文档 ID")
    # PDF 文档 ID，必填
    
    model: Optional[str] = Field(None, description="LLM 模型")
    # LLM 模型，可选
    
    user_id: Optional[str] = Field(None, description="用户 ID")
    # 用户 ID，可选

    @validator('message')
    def validate_message(cls, v):
        """验证消息 - 不能为空，去除首尾空格"""
        if not v or not v.strip():
            raise ValueError("消息不能为空")
        return v.strip()


class DocumentSource(BaseModel):
    """
    文档来源 - 表示回答的来源信息
    
    示例：
        {
            "page_number": 5,
            "similarity": 0.85,
            "preview": "机器学习是..."
        }
    """
    page_number: Optional[int] = None
    # 页码，可选
    
    similarity: Optional[float] = None
    # 相似度（0.0-1.0），可选
    
    preview: str
    # 内容预览


class ChatMetadata(BaseModel):
    """
    聊天元数据 - 记录聊天的详细信息
    
    示例：
        {
            "pdf_name": "机器学习入门.pdf",
            "total_pages": 100,
            "total_chunks": 500,
            "chunks_retrieved": 5,
            "sources": [...],
            "model": "deepseek/deepseek-chat-v3.1",
            "rag_enabled": true,
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    pdf_name: str
    # PDF 文件名
    
    total_pages: Optional[int] = None
    # 总页数，可选
    
    total_chunks: int
    # 总文档块数
    
    chunks_retrieved: int
    # 检索到的文档块数
    
    sources: List[DocumentSource]
    # 文档来源列表
    
    model: str
    # 使用的 LLM 模型
    
    rag_enabled: bool = True
    # 是否启用 RAG
    
    timestamp: datetime
    # 时间戳


class ChatResponse(BaseModel):
    """
    RAG 聊天响应
    
    示例：
        {
            "success": true,
            "response": "机器学习是...",
            "metadata": {...}
        }
    """
    success: bool
    # 是否成功
    
    response: str
    # LLM 生成的回答
    
    metadata: ChatMetadata
    # 聊天元数据


class RetrievalRequest(BaseModel):
    """
    检索请求
    
    示例：
        {
            "query": "什么是机器学习？",
            "pdf_id": "123",
            "top_k": 5,
            "threshold": 0.6
        }
    """
    query: str = Field(..., min_length=1)
    # 检索查询，必填
    
    pdf_id: Optional[str] = None
    # PDF 文档 ID，可选（限制检索范围）
    
    top_k: int = Field(5, ge=1, le=20)
    # 返回的文档块数量，默认 5，范围 1-20
    
    threshold: float = Field(0.6, ge=0.0, le=1.0)
    # 相似度阈值，默认 0.6，范围 0.0-1.0


class ChunkResult(BaseModel):
    """
    检索结果 - 表示一个检索到的文档块
    
    示例：
        {
            "id": "chunk_123",
            "pdf_id": "123",
            "pdf_name": "机器学习入门.pdf",
            "chunk_index": 0,
            "content": "机器学习是...",
            "page_number": 5,
            "similarity": 0.85,
            "token_count": 100
        }
    """
    id: str
    # 文档块 ID
    
    pdf_id: str
    # PDF 文档 ID
    
    pdf_name: str
    # PDF 文件名
    
    chunk_index: int
    # 文档块索引
    
    content: str
    # 文档块内容
    
    page_number: Optional[int] = None
    # 页码，可选
    
    similarity: float
    # 相似度（0.0-1.0）
    
    token_count: int
    # Token 数量


class RetrievalResponse(BaseModel):
    """
    检索响应
    
    示例：
        {
            "success": true,
            "chunks": [...],
            "total": 5,
            "query_rewrite": {"original": "...", "rewritten": "..."}
        }
    """
    success: bool
    # 是否成功
    
    chunks: List[ChunkResult]
    # 文档块列表
    
    total: int
    # 总数量
    
    query_rewrite: Optional[Dict[str, Any]] = None
    # 查询重写信息，可选


# ============================================================================
# 系统相关模型
# ============================================================================

class HealthResponse(BaseModel):
    """
    健康检查响应
    
    示例：
        {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00",
            "cache_enabled": true,
            "cache_stats": {...}
        }
    """
    status: str
    # 服务状态：healthy / unhealthy
    
    version: str
    # 服务版本号
    
    timestamp: datetime
    # 检查时间戳
    
    cache_enabled: bool
    # 是否启用缓存
    
    cache_stats: Optional[Dict[str, Any]] = None
    # 缓存统计，可选


class ErrorResponse(BaseModel):
    """
    错误响应
    
    示例：
        {
            "error": "数据库连接失败",
            "details": "无法连接到 PostgreSQL",
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    error: str
    # 错误信息（简短）
    
    details: Optional[str] = None
    # 详细错误信息，可选
    
    timestamp: datetime
    # 错误发生时间


# ============================================================================
# Pydantic 验证说明
# ============================================================================
# Pydantic 提供强大的数据验证功能：
#
# 1. 类型验证
#    - 自动验证字段类型
#    - 示例：age: int → 自动将 "25" 转换为 25
#
# 2. 约束验证
#    - Field() 定义约束
#    - 示例：Field(min_length=1, max_length=100)
#
# 3. 自定义验证
#    - @validator 装饰器
#    - 示例：@validator('email') def validate_email(cls, v): ...
#
# 4. 错误处理
#    - 验证失败时抛出 ValidationError
#    - FastAPI 自动返回 422 错误

# ============================================================================
# Field() 参数说明
# ============================================================================
# Field() 用于定义字段的约束和元数据：
#
# 常用参数：
#   - default: 默认值
#   - ...: 必填（无默认值）
#   - description: 字段描述（用于 API 文档）
#   - min_length, max_length: 字符串长度约束
#   - min_items, max_items: 列表长度约束
#   - ge, le: 数值范围约束（greater or equal, less or equal）
#   - gt, lt: 数值范围约束（greater than, less than）
#
# 示例：
#   age: int = Field(..., ge=0, le=150, description="年龄")
#   name: str = Field(..., min_length=1, max_length=50)
#   tags: List[str] = Field([], min_items=0, max_items=10)

# ============================================================================
# @validator 装饰器说明
# ============================================================================
# @validator 用于自定义验证逻辑：
#
# 基本用法：
#   @validator('field_name')
#   def validate_field(cls, v):
#       if not valid(v):
#           raise ValueError("错误信息")
#       return v
#
# 参数说明：
#   - cls: 类本身（类方法）
#   - v: 字段的值
#
# 返回值：
#   - 验证后的值（可以修改）
#
# 错误处理：
#   - 抛出 ValueError
#   - FastAPI 自动返回 422 错误

# ============================================================================
# BaseModel 方法说明
# ============================================================================
# Pydantic BaseModel 提供的常用方法：
#
# 1. dict()
#    - 转换为字典
#    - 示例：request.dict()
#
# 2. json()
#    - 转换为 JSON 字符串
#    - 示例：request.json()
#
# 3. parse_obj()
#    - 从字典创建对象
#    - 示例：Request.parse_obj({"message": "你好"})
#
# 4. parse_raw()
#    - 从 JSON 字符串创建对象
#    - 示例：Request.parse_raw('{"message": "你好"}')
#
# 5. copy()
#    - 复制对象
#    - 示例：request2 = request.copy()

# ============================================================================
# FastAPI 集成说明
# ============================================================================
# FastAPI 自动集成 Pydantic：
#
# 1. 请求验证
#    - 自动验证请求体
#    - 验证失败返回 422 错误
#
# 2. 响应序列化
#    - 自动将对象转换为 JSON
#    - 示例：return ChatResponse(...)
#
# 3. API 文档
#    - 自动生成 OpenAPI 文档
#    - 包含字段描述和约束
#
# 4. 类型提示
#    - 提供 IDE 自动补全
#    - 提供类型检查
