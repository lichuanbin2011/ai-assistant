"""
============================================================================
配置管理模块
============================================================================

文件位置：
  rag-service/app/core/config.py

文件作用：
  管理应用的所有配置项，支持环境变量和 .env 文件

主要功能：
  1. 配置定义 - 定义所有配置项及其默认值
  2. 环境变量 - 支持从环境变量读取配置
  3. .env 文件 - 支持从 .env 文件读取配置
  4. 单例模式 - 使用 lru_cache 实现配置单例

配置分类：
  - API 配置：OpenRouter API、Embedding 模型
  - LLM 配置：主模型、重写模型、回退模型
  - 数据库配置：PostgreSQL 连接、连接池
  - 应用配置：名称、版本、URL
  - 服务配置：主机、端口、调试模式
  - 缓存配置：启用、大小、TTL
  - 批处理配置：批大小、重试次数
  - RAG 配置：分块、检索、查询重写
  - 限流配置：每分钟请求数

技术栈：
  - Pydantic Settings（配置管理）
  - functools.lru_cache（单例模式）

依赖文件：
  - .env（环境变量文件，可选）

============================================================================
"""
from pydantic_settings import BaseSettings  # Pydantic 配置管理
from functools import lru_cache  # LRU 缓存装饰器（实现单例）
from typing import Optional  # 类型注解


# ============================================================================
# 配置类
# ============================================================================

class Settings(BaseSettings):
    """
    应用配置
    
    功能说明：
      - 定义所有配置项及其默认值
      - 支持从环境变量读取配置
      - 支持从 .env 文件读取配置
      - 自动类型转换和验证
    
    配置优先级：
      1. 环境变量（最高优先级）
      2. .env 文件
      3. 默认值（最低优先级）
    
    使用示例：
        ```python
        from app.core.config import get_settings
        
        settings = get_settings()
        print(settings.OPENROUTER_API_KEY)
        print(settings.DATABASE_URL)
        ```
    
    环境变量示例：
        ```bash
        export OPENROUTER_API_KEY="sk-xxx"
        export DATABASE_URL="postgresql://user:pass@localhost/db"
        ```
    
    .env 文件示例：
        ```
        OPENROUTER_API_KEY=sk-xxx
        DATABASE_URL=postgresql://user:pass@localhost/db
        ```
    """

    # ========================================================================
    # API 配置
    # ========================================================================
    # 功能说明：
    #   - OpenRouter API 配置（用于调用 LLM）
    #   - Embedding 模型配置（用于向量化）
    
    OPENROUTER_API_KEY: str = "Your OPENROUTER_API_KEY "
    # 说明：
    #   - OpenRouter API 密钥
    #   - 用于调用 LLM（查询重写、对话生成）
    #   - 必须设置（默认值无效）
    #   - 获取方式：https://openrouter.ai/keys
    
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # 说明：
    #   - OpenRouter API 基础 URL
    #   - 默认值：https://openrouter.ai/api/v1
    #   - 通常不需要修改
    
    EMBEDDING_MODEL: str = "baai/bge-m3"
    # 说明：
    #   - Embedding 模型名称
    #   - 用于文本向量化
    #   - 默认：baai/bge-m3（中英文通用模型）
    #   - 其他选项：
    #     - sentence-transformers/all-MiniLM-L6-v2（英文）
    #     - sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2（多语言）

    # ========================================================================
    # LLM 模型配置
    # ========================================================================
    # 功能说明：
    #   - 主模型：用于对话生成
    #   - 重写模型：用于查询重写
    #   - 回退模型：主模型失败时使用
    
    LLM_MODEL_MAIN: str = "deepseek/deepseek-chat-v3.1"
    # 说明：
    #   - 主对话模型
    #   - 用于生成回答
    #   - 默认：deepseek-chat-v3.1（性能强，成本低）
    #   - 其他选项：
    #     - anthropic/claude-3.5-sonnet（高质量）
    #     - openai/gpt-4-turbo（高质量）
    #     - google/gemini-pro（免费）
    
    LLM_MODEL_REWRITE: str = "deepseek/deepseek-chat"
    # 说明：
    #   - 查询重写模型
    #   - 用于优化用户查询
    #   - 默认：deepseek-chat（成本低，速度快）
    #   - 要求：速度快、成本低（查询重写不需要高质量）
    
    LLM_MODEL_FALLBACK: str = "deepseek/deepseek-chat"
    # 说明：
    #   - 回退模型
    #   - 主模型失败时使用
    #   - 默认：deepseek-chat（稳定性高）
    #   - 要求：稳定性高、可用性高

    # ========================================================================
    # PostgreSQL 配置
    # ========================================================================
    # 功能说明：
    #   - 数据库连接配置
    #   - 连接池配置
    
    DATABASE_URL: str = "postgresql://postgres:your password@postgres:5432/ai_chat"
    # 说明：
    #   - PostgreSQL 连接字符串
    #   - 格式：postgresql://用户名:密码@主机:端口/数据库名
    #   - 示例：postgresql://postgres:password@localhost:5432/ai_chat
    #   - 必须设置（默认值无效）
    #   - 注意：密码中的特殊字符需要 URL 编码
    
    DATABASE_POOL_SIZE: int = 10
    # 说明：
    #   - 数据库连接池大小
    #   - 默认：10
    #   - 说明：同时保持的数据库连接数
    #   - 建议：根据并发请求数调整（10-50）
    
    DATABASE_MAX_OVERFLOW: int = 20
    # 说明：
    #   - 数据库连接池最大溢出数
    #   - 默认：20
    #   - 说明：连接池满时，最多额外创建的连接数
    #   - 总连接数 = POOL_SIZE + MAX_OVERFLOW

    # ========================================================================
    # 应用信息
    # ========================================================================
    # 功能说明：
    #   - 应用的基本信息
    #   - 用于日志、监控、API 调用
    
    APP_NAME: str = "AI Chat App - Embedding Service"
    # 说明：
    #   - 应用名称
    #   - 用于日志、监控
    
    APP_URL: str = "http://localhost:3000"
    # 说明：
    #   - 应用 URL
    #   - 用于 OpenRouter API 调用（HTTP-Referer）
    
    APP_VERSION: str = "1.0.0"
    # 说明：
    #   - 应用版本号
    #   - 用于日志、监控

    # ========================================================================
    # 服务配置
    # ========================================================================
    # 功能说明：
    #   - FastAPI 服务配置
    #   - 主机、端口、调试模式
    
    HOST: str = "0.0.0.0"
    # 说明：
    #   - 监听主机
    #   - 0.0.0.0：监听所有网络接口
    #   - 127.0.0.1：只监听本地
    
    PORT: int = 8001
    # 说明：
    #   - 监听端口
    #   - 默认：8001
    #   - 注意：避免与其他服务冲突
    
    DEBUG: bool = False
    # 说明：
    #   - 调试模式
    #   - True：启用调试日志、自动重载
    #   - False：生产模式
    #   - 生产环境必须设置为 False

    # ========================================================================
    # 缓存配置
    # ========================================================================
    # 功能说明：
    #   - 内存缓存配置
    #   - 用于缓存向量化结果
    
    CACHE_ENABLED: bool = True
    # 说明：
    #   - 是否启用缓存
    #   - True：启用（推荐）
    #   - False：禁用（调试时使用）
    
    CACHE_MAX_SIZE: int = 1000
    # 说明：
    #   - 缓存最大条目数
    #   - 默认：1000
    #   - 说明：缓存满时自动删除最旧条目
    #   - 内存估算：1000 条目 ≈ 4MB
    
    CACHE_TTL_SECONDS: int = 3600  # 1小时
    # 说明：
    #   - 缓存过期时间（秒）
    #   - 默认：3600（1 小时）
    #   - 说明：超过此时间的缓存会被删除
    #   - 建议：根据数据更新频率调整

    # ========================================================================
    # 批处理配置
    # ========================================================================
    # 功能说明：
    #   - 批量向量化配置
    #   - 重试配置
    
    BATCH_SIZE: int = 50
    # 说明：
    #   - 批处理大小
    #   - 默认：50
    #   - 说明：一次向量化的文本数量
    #   - 建议：根据模型和内存调整（10-100）
    
    MAX_RETRIES: int = 3
    # 说明：
    #   - 最大重试次数
    #   - 默认：3
    #   - 说明：向量化失败时的重试次数
    
    RETRY_DELAY: float = 1.0
    # 说明：
    #   - 重试延迟（秒）
    #   - 默认：1.0
    #   - 说明：重试前等待的时间

    # ========================================================================
    # RAG 配置
    # ========================================================================
    # 功能说明：
    #   - 文本分块配置
    #   - 检索配置
    #   - 查询重写配置
    
    # ========== 文本分块 ==========
    CHUNK_SIZE: int = 1000
    # 说明：
    #   - 文本块大小（字符数）
    #   - 默认：1000
    #   - 说明：每个文本块的最大字符数
    #   - 建议：
    #     - 中文：500-1000
    #     - 英文：1000-2000
    
    CHUNK_OVERLAP: int = 200
    # 说明：
    #   - 文本块重叠大小（字符数）
    #   - 默认：200
    #   - 说明：相邻文本块的重叠部分
    #   - 建议：CHUNK_SIZE 的 10-20%

    # ========== 检索配置 ==========
    RETRIEVAL_TOP_K: int = 5
    # 说明：
    #   - 检索返回的文档块数量
    #   - 默认：5
    #   - 说明：返回相似度最高的 K 个文档块
    #   - 建议：
    #     - 精确回答：1-3
    #     - 标准回答：3-5
    #     - 详细回答：5-10
    
    SIMILARITY_THRESHOLD: float = 0.6
    # 说明：
    #   - 相似度阈值
    #   - 默认：0.6
    #   - 说明：只返回相似度 >= 阈值的文档块
    #   - 范围：0-1
    #   - 建议：
    #     - 严格模式：0.8-1.0
    #     - 标准模式：0.6-0.8
    #     - 宽松模式：0.4-0.6

    # ========== 查询重写 ==========
    ENABLE_QUERY_REWRITE: bool = True
    # 说明：
    #   - 是否启用查询重写
    #   - True：启用（推荐）
    #   - False：禁用
    #   - 功能：优化用户查询，提高检索效果

    # ========================================================================
    # API 限流配置
    # ========================================================================
    # 功能说明：
    #   - 限制 API 请求频率
    #   - 防止滥用
    
    RATE_LIMIT_PER_MINUTE: int = 60
    # 说明：
    #   - 每分钟最大请求数
    #   - 默认：60
    #   - 说明：超过此限制会返回 429 错误
    #   - 建议：根据服务器性能调整

    # ========================================================================
    # Pydantic 配置
    # ========================================================================
    class Config:
        """
        Pydantic 配置类
        
        功能说明：
          - 配置 Pydantic 的行为
          - 指定 .env 文件路径
          - 配置大小写敏感
        """
        env_file = ".env"
        # 说明：
        #   - 从 .env 文件读取配置
        #   - 路径：项目根目录的 .env 文件
        #   - 如果文件不存在，不会报错
        
        case_sensitive = True
        # 说明：
        #   - 环境变量名大小写敏感
        #   - True：OPENROUTER_API_KEY ≠ openrouter_api_key
        #   - False：OPENROUTER_API_KEY = openrouter_api_key


# ============================================================================
# 工厂函数（单例模式）
# ============================================================================

@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    
    功能说明：
      - 使用 lru_cache 实现单例模式
      - 第一次调用时创建实例
      - 后续调用返回同一个实例
    
    单例原理：
      - lru_cache() 缓存函数的返回值
      - 相同参数的调用返回缓存的结果
      - 无参数函数只会执行一次
    
    Returns:
        Settings: 配置实例
    
    使用示例：
        ```python
        from app.core.config import get_settings
        
        # 第一次调用，创建实例
        settings = get_settings()
        
        # 后续调用，返回同一个实例
        settings2 = get_settings()
        
        # settings 和 settings2 是同一个对象
        assert settings is settings2
        ```
    """
    return Settings()


# ============================================================================
# 配置优先级说明
# ============================================================================
# Pydantic Settings 的配置读取顺序（优先级从高到低）：
#
# 1. 环境变量（最高优先级）
#    - 直接设置的环境变量
#    - 示例：export OPENROUTER_API_KEY="sk-xxx"
#
# 2. .env 文件
#    - 项目根目录的 .env 文件
#    - 示例：OPENROUTER_API_KEY=sk-xxx
#
# 3. 默认值（最低优先级）
#    - 代码中定义的默认值
#    - 示例：OPENROUTER_API_KEY: str = "Your OPENROUTER_API_KEY"

# ============================================================================
# 环境变量命名规范
# ============================================================================
# 1. 全大写
#    - 示例：OPENROUTER_API_KEY
#
# 2. 使用下划线分隔
#    - 示例：DATABASE_POOL_SIZE
#
# 3. 前缀（可选）
#    - 示例：APP_NAME, DATABASE_URL
#
# 4. 避免特殊字符
#    - 只使用字母、数字、下划线

# ============================================================================
# .env 文件示例
# ============================================================================
# ```
# # API 配置
# OPENROUTER_API_KEY=sk-xxx
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# EMBEDDING_MODEL=baai/bge-m3
#
# # LLM 配置
# LLM_MODEL_MAIN=deepseek/deepseek-chat-v3.1
# LLM_MODEL_REWRITE=deepseek/deepseek-chat
# LLM_MODEL_FALLBACK=deepseek/deepseek-chat
#
# # 数据库配置
# DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_chat
# DATABASE_POOL_SIZE=10
# DATABASE_MAX_OVERFLOW=20
#
# # 应用配置
# APP_NAME=AI Chat App - Embedding Service
# APP_URL=http://localhost:3000
# APP_VERSION=1.0.0
#
# # 服务配置
# HOST=0.0.0.0
# PORT=8001
# DEBUG=False
#
# # 缓存配置
# CACHE_ENABLED=True
# CACHE_MAX_SIZE=1000
# CACHE_TTL_SECONDS=3600
#
# # RAG 配置
# CHUNK_SIZE=1000
# CHUNK_OVERLAP=200
# RETRIEVAL_TOP_K=5
# SIMILARITY_THRESHOLD=0.6
# ENABLE_QUERY_REWRITE=True
# ```

# ============================================================================
# 配置验证
# ============================================================================
# Pydantic 会自动验证配置：
#
# 1. 类型验证
#    - 示例：PORT 必须是整数
#    - 错误：PORT=abc → ValidationError
#
# 2. 必填字段
#    - 示例：OPENROUTER_API_KEY 必须设置
#    - 错误：未设置 → ValidationError
#
# 3. 范围验证（可选）
#    - 使用 Field() 定义范围
#    - 示例：PORT: int = Field(ge=1, le=65535)

# ============================================================================
# 配置最佳实践
# ============================================================================
# 1. 敏感信息
#    - 不要在代码中硬编码
#    - 使用环境变量或 .env 文件
#    - .env 文件不要提交到 Git
#
# 2. 默认值
#    - 为所有配置提供合理的默认值
#    - 生产环境必须覆盖敏感配置
#
# 3. 文档
#    - 为每个配置添加注释
#    - 说明配置的用途和建议值
#
# 4. 验证
#    - 使用 Pydantic 的验证功能
#    - 确保配置的正确性
#
# 5. 环境隔离
#    - 开发、测试、生产使用不同的配置
#    - 使用不同的 .env 文件
