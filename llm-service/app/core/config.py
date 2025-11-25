"""
============================================================================
配置管理
使用 Pydantic Settings 进行环境变量管理
============================================================================

文件位置：
  llm-service/app/core/config.py

文件作用：
  统一管理应用配置，从环境变量和 .env 文件加载配置

主要功能：
  1. 环境变量加载 - 从 .env 文件读取配置
  2. 类型验证 - 使用 Pydantic 自动验证配置类型
  3. 默认值管理 - 为每个配置项提供合理的默认值
  4. 全局配置实例 - 提供单例配置对象

配置分类：
  - 应用配置（名称、版本、环境）
  - 服务配置（主机、端口）
  - OpenRouter 配置（API Key、模型）
  - 博查搜索配置（API Key、超时）
  - CORS 配置（跨域白名单）
  - 日志配置（级别、文件路径）
  - LLM 配置（温度、token 数）

技术栈：
  - Pydantic Settings（配置管理）
  - Python dotenv（环境变量加载）

使用方式：
  from app.core.config import settings
  print(settings.OPENROUTER_API_KEY)

依赖文件：
  - .env（环境变量文件，位于项目根目录）

============================================================================
"""
import os  # 操作系统接口
from pathlib import Path  # 路径操作（面向对象）
from typing import List, Optional  # 类型注解
from pydantic_settings import BaseSettings, SettingsConfigDict  # Pydantic 配置管理
from pydantic import Field  # 字段定义和验证

# ============================================================================
# 路径配置
# ============================================================================
# 获取项目根目录
# __file__ = 当前文件路径（config.py）
# .parent = app/core
# .parent.parent = app
# .parent.parent.parent = llm-service（项目根目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# .env 文件路径（位于项目根目录）
ENV_FILE = BASE_DIR / ".env"


# ============================================================================
# 配置类定义
# ============================================================================
class Settings(BaseSettings):
    """
    应用配置类
    
    功能说明：
      - 使用 Pydantic Settings 自动从环境变量加载配置
      - 支持类型验证和默认值
      - 支持从 .env 文件读取配置
    
    配置优先级：
      1. 环境变量（最高优先级）
      2. .env 文件
      3. 默认值（最低优先级）
    """

    # ==================== 应用配置 ====================
    # 应用基本信息配置
    APP_NAME: str = Field(default="LLM Service", description="应用名称")  # 应用名称（用于日志、监控）
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")  # 版本号（用于健康检查）
    ENVIRONMENT: str = Field(default="development", description="运行环境")  # 运行环境（development/staging/production）
    DEBUG: bool = Field(default=True, description="调试模式")  # 调试模式（开启后显示详细错误信息）

    # ==================== 服务配置 ====================
    # Web 服务监听配置
    HOST: str = Field(default="0.0.0.0", description="监听地址")  # 监听地址（0.0.0.0 表示监听所有网卡）
    PORT: int = Field(default=8002, description="监听端口")  # 监听端口（默认 8002）

    # ==================== OpenRouter API ====================
    # OpenRouter LLM 服务配置
    OPENROUTER_API_KEY: str = Field(default='Your OPENROUTER_API_KEY', description="OpenRouter API Key")  # API 密钥（必须配置）
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",  # OpenRouter API 地址
        description="OpenRouter API 基础 URL"
    )
    OPENROUTER_DEFAULT_MODEL: str = Field(
        default="openai/gpt-4o-mini",  # 默认模型（性价比高）
        description="OpenRouter 默认模型"
    )

    # ==================== CORS 配置 ====================
    # 跨域资源共享配置（允许前端访问）
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",  # React 开发服务器
            "http://localhost:8000",  # 后端主服务
            "http://localhost:8002"   # 当前服务
        ],
        description="允许的跨域源"
    )

    # ==================== 日志配置 ====================
    # 日志记录配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")  # 日志级别（DEBUG/INFO/WARNING/ERROR）
    LOG_FILE: str = Field(default="logs/llm-service.log", description="日志文件路径")  # 日志文件路径（相对于项目根目录）

    # ==================== LLM 配置 ====================
    # LLM 生成参数默认值
    DEFAULT_TEMPERATURE: float = Field(default=0.7, ge=0, le=2, description="默认温度参数")  # 温度（0=确定性，2=随机性）
    DEFAULT_MAX_TOKENS: int = Field(default=2000, ge=1, description="默认最大 token 数")  # 最大生成长度
    DEFAULT_STREAMING: bool = Field(default=True, description="默认是否启用流式输出")  # 是否启用流式传输

    # ==================== 超时配置 ====================
    # 请求超时配置
    REQUEST_TIMEOUT: int = Field(default=60, description="请求超时时间（秒）")  # HTTP 请求超时时间

    #  ==================== 博查搜索配置 ====================
    # 博查 AI 搜索服务配置
    BOCHA_API_KEY: Optional[str] = Field(
        default="Your BOCHA_API_KEY",  # API 密钥（可选，用于联网搜索）
        description="博查 AI API Key（可选，用于联网搜索）"
    )
    BOCHA_API_URL: str = Field(
        default="https://api.bochaai.com/v1/web-search",  # 博查 API 地址
        description="博查 API 地址"
    )
    BOCHA_MAX_RESULTS: int = Field(
        default=10,  # 默认返回 10 条搜索结果
        ge=1,  # 最小值 1
        le=20,  # 最大值 20
        description="博查搜索最大结果数"
    )
    BOCHA_TIMEOUT: int = Field(
        default=30,  # 默认超时 30 秒
        ge=5,  # 最小值 5 秒
        le=60,  # 最大值 60 秒
        description="博查搜索超时时间（秒）"
    )
    BOCHA_DEFAULT_FRESHNESS: str = Field(
        default="noLimit",  # 默认不限制时间范围
        description="博查搜索时间范围（noLimit/day/week/month）"
    )
    #  ==================== END ====================

    # ============================================================================
    # Pydantic v2 标准配置
    # ============================================================================
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),  # .env 文件路径
        env_file_encoding="utf-8",  # 文件编码（支持中文）
        case_sensitive=True,  # 环境变量名称区分大小写
        extra="ignore"  # 忽略未定义的环境变量（避免报错）
    )


# ============================================================================
# 全局配置实例
# ============================================================================
# 创建全局配置实例（单例模式）
# 在应用启动时自动加载配置
settings = Settings()

# ============================================================================
# 初始化操作
# ============================================================================
# 确保日志目录存在
# 如果日志目录不存在，自动创建（包括父目录）
log_dir = Path(settings.LOG_FILE).parent  # 获取日志文件的父目录
log_dir.mkdir(parents=True, exist_ok=True)  # 创建目录（parents=True 表示创建父目录，exist_ok=True 表示目录存在时不报错）
