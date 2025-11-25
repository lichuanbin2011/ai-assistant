"""
============================================================================
FastAPI 主入口文件
============================================================================

文件位置：
  rag-service/app/main.py

文件作用：
  FastAPI 应用的主入口，负责应用的初始化、配置和启动

主要功能：
  1. 应用初始化 - 创建 FastAPI 应用实例
  2. 生命周期管理 - 启动/关闭时的资源管理
  3. 路由注册 - 注册所有 API 路由
  4. 中间件配置 - CORS、日志等
  5. 健康检查 - 监控服务状态
  6. 缓存管理 - 缓存统计和清理

技术栈：
  - FastAPI（Web 框架）
  - Uvicorn（ASGI 服务器）
  - Loguru（日志记录）
  - asyncpg（数据库连接）

依赖文件：
  - app/core/config.py（配置管理）
  - app/core/database.py（数据库）
  - app/core/cache.py（缓存）
  - app/api/v1/*（API 路由）
  - app/services/*（业务服务）

API 路由结构：
  - /api/v1/embed/*        - Embedding 向量化
  - /api/v1/chat           - RAG 聊天
  - /api/v1/retrieval      - 向量检索
  - /api/v1/documents/*    - 文档管理
  - /api/v1/pdf/*          - PDF 处理
  - /health                - 健康检查
  - /api/v1/cache/*        - 缓存管理

启动方式：
  1. 开发模式：python app/main.py
  2. 生产模式：uvicorn app.main:app --host 0.0.0.0 --port 8001

服务监控：
  - 健康检查：GET /health
  - API 文档：GET /docs
  - 缓存统计：GET /api/v1/cache/stats

============================================================================
"""

# ============================================================================
# 导入依赖模块
# ============================================================================

# 在文件顶部导入所有路由模块
from app.api.v1 import embed, chat, retrieval, documents, pdf  # 添加 pdf

# FastAPI 核心模块
from fastapi import FastAPI  # FastAPI 应用类
from fastapi.middleware.cors import CORSMiddleware  # CORS 中间件（跨域支持）
from contextlib import asynccontextmanager  # 异步上下文管理器（生命周期管理）
from datetime import datetime  # 时间处理
from loguru import logger  # 日志记录库
import sys  # 系统模块（用于日志输出）

# 应用核心模块
from app.core.config import get_settings  # 配置管理
from app.core.database import get_database  # 数据库连接
from app.api.v1 import embed, chat, retrieval, documents  # API 路由
from app.core.cache import get_cache  # 缓存服务
from app.services.embedding import get_embedding_service  # Embedding 服务
from app.services.llm import get_llm_service  # LLM 服务

# ============================================================================
# 配置日志系统
# ============================================================================

# 移除默认的日志处理器（避免重复输出）
logger.remove()

# 添加自定义日志处理器（输出到标准输出）
logger.add(
    sys.stdout,  # 输出目标：标准输出（控制台）
    # 日志格式：时间 | 级别 | 模块:函数:行号 - 消息
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"  # 日志级别：INFO（记录 INFO、WARNING、ERROR）
)

# ============================================================================
# 加载配置
# ============================================================================

settings = get_settings()  # 获取全局配置实例


# ============================================================================
# 应用生命周期管理
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    
    功能说明：
        管理应用启动和关闭时的资源初始化和清理
        使用异步上下文管理器（async with）模式
    
    工作流程：
        1. 启动时（yield 之前）：
           - 打印启动信息
           - 连接数据库
           - 初始化服务
        
        2. 运行时（yield）：
           - 应用正常运行
        
        3. 关闭时（yield 之后）：
           - 断开数据库连接
           - 清理资源
    
    生命周期：
        启动 → yield → 运行 → yield 之后 → 关闭
    """
    # ========================================================================
    # 启动时（Startup）
    # ========================================================================
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  - Embedding 模型: {settings.EMBEDDING_MODEL}")
    logger.info(f"  - LLM 模型: {settings.LLM_MODEL_MAIN}")
    logger.info(f"  - 缓存: {'启用' if settings.CACHE_ENABLED else '禁用'}")
    logger.info(f"  - 监听: {settings.HOST}:{settings.PORT}")

    # 连接数据库
    db = get_database()  # 获取数据库实例
    await db.connect()  # 建立数据库连接

    yield  # 让出控制权，应用开始运行

    # ========================================================================
    # 关闭时（Shutdown）
    # ========================================================================
    logger.info("正在关闭服务...")
    await db.disconnect()  # 断开数据库连接


# ============================================================================
# 创建 FastAPI 应用实例
# ============================================================================

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,  # 应用名称（显示在 API 文档中）
    version=settings.APP_VERSION,  # 应用版本
    lifespan=lifespan,  # 生命周期管理器
    docs_url="/docs",  # Swagger UI 文档地址
    redoc_url="/redoc",  # ReDoc 文档地址
)

# ============================================================================
# 配置 CORS 中间件（跨域资源共享）
# ============================================================================

# CORS 配置（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,  # CORS 中间件
    allow_origins=["*"],  # 允许所有来源（生产环境应限制具体域名）
    allow_credentials=True,  # 允许携带 Cookie
    allow_methods=["*"],  # 允许所有 HTTP 方法（GET、POST、PUT、DELETE 等）
    allow_headers=["*"],  # 允许所有请求头
)

# ============================================================================
# 注册 API 路由
# ============================================================================

# Embedding 路由（向量化服务）
# 路径：/api/v1/embed/*
# 功能：文本向量化、批量向量化
app.include_router(
    embed.router,  # 路由对象
    prefix="/api/v1/embed",  # 路由前缀
    tags=["Embedding"]  # API 文档标签
)

# RAG 聊天路由（问答服务）
# 路径：/api/v1/chat
# 功能：基于检索的问答
app.include_router(
    chat.router,
    prefix="/api/v1",
    tags=["RAG Chat"]
)

# 检索路由（向量检索服务）
# 路径：/api/v1/retrieval
# 功能：向量相似度检索
app.include_router(
    retrieval.router,
    prefix="/api/v1",
    tags=["Retrieval"]
)

# 文档管理路由（文档 CRUD）
# 路径：/api/v1/documents/*
# 功能：文档上传、查询、删除
app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["Documents"]
)

# 在路由注册部分添加PDF 处理路由（PDF 处理服务）
# 路径：/api/v1/pdf/*
# 功能：PDF 上传、解析、分块、向量化
app.include_router(
    pdf.router,
    prefix="/api/v1/pdf",
    tags=["PDF Processing"]
)


# ============================================================================
# 基础路由（根路径和健康检查）
# ============================================================================

@app.get("/")
async def root():
    """
    根路径
    
    功能说明：
        返回服务的基本信息
    
    返回示例：
        {
            "service": "AI Chat App - RAG Service",
            "version": "2.0.0",
            "embedding_model": "text-embedding-3-small",
            "llm_model": "gpt-4",
            "docs": "/docs"
        }
    """
    return {
        "service": settings.APP_NAME,  # 服务名称
        "version": settings.APP_VERSION,  # 版本号
        "embedding_model": settings.EMBEDDING_MODEL,  # Embedding 模型
        "llm_model": settings.LLM_MODEL_MAIN,  # LLM 模型
        "docs": "/docs",  # API 文档地址
    }


@app.get("/health")
async def health_check():
    """
    健康检查端点
    
    功能说明：
        检查服务的各个组件是否正常运行
        用于监控系统（如 Kubernetes、Docker）
    
    检查项目：
        - 数据库连接
        - 缓存服务
        - Embedding 服务
        - LLM 服务
    
    返回状态：
        - healthy: 所有组件正常
        - degraded: 部分组件异常（如数据库断开）
        - unhealthy: 服务异常
    
    返回示例：
        {
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": "2025-11-25T14:33:00",
            "services": {
                "database": true,
                "cache": true,
                "embedding": true,
                "llm": true
            },
            "cache_stats": {
                "hits": 100,
                "misses": 20,
                "hit_rate": 0.833
            }
        }
    """
    try:
        # ====================================================================
        # 检查数据库连接
        # ====================================================================
        db_healthy = False  # 数据库健康状态（默认 False）
        try:
            db = get_database()  # 获取数据库实例
            if db._connected:  # 检查是否已连接
                # 修复：测试查询（执行简单查询验证连接）
                await db.fetchval("SELECT 1")
                db_healthy = True  # 标记为健康
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")

        # ====================================================================
        # 检查缓存服务
        # ====================================================================
        cache_enabled = settings.CACHE_ENABLED  # 缓存是否启用
        cache_stats = None  # 缓存统计（默认 None）
        if cache_enabled:
            try:
                cache = get_cache()  # 获取缓存实例
                cache_stats = cache.get_stats()  # 获取缓存统计
            except:
                pass  # 忽略缓存错误（不影响整体健康状态）

        # ====================================================================
        # 检查 Embedding 服务
        # ====================================================================
        embedding_healthy = False  # Embedding 服务健康状态
        try:
            embedding_service = get_embedding_service()  # 获取服务实例
            embedding_healthy = True  # 标记为健康
        except:
            pass

        # ====================================================================
        # 检查 LLM 服务
        # ====================================================================
        llm_healthy = False  # LLM 服务健康状态
        try:
            llm_service = get_llm_service()  # 获取服务实例
            llm_healthy = True  # 标记为健康
        except:
            pass

        # ====================================================================
        # 计算整体状态
        # ====================================================================
        # 如果数据库正常，则整体状态为 healthy，否则为 degraded
        overall_status = "healthy" if db_healthy else "degraded"

        # 返回健康检查结果
        return {
            "status": overall_status,  # 整体状态
            "version": "2.0.0",  # 版本号
            "timestamp": datetime.now().isoformat(),  # 当前时间
            "services": {  # 各组件状态
                "database": db_healthy,
                "cache": cache_enabled,
                "embedding": embedding_healthy,
                "llm": llm_healthy,
            },
            "cache_stats": cache_stats,  # 缓存统计（可选）
        }

    except Exception as e:
        # 如果健康检查本身失败，返回 unhealthy
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# ============================================================================
# 缓存管理路由
# ============================================================================

@app.delete("/api/v1/cache")
async def clear_cache():
    """
    清空缓存
    
    功能说明：
        清空所有缓存数据（用于调试或强制刷新）
    
    使用场景：
        - 更新 Embedding 模型后清空旧缓存
        - 调试时清空缓存
        - 释放内存
    
    返回示例：
        {
            "message": "缓存已清空",
            "deleted_keys": 150
        }
    """
    # 检查缓存是否启用
    if not settings.CACHE_ENABLED:
        return {"message": "缓存未启用"}

    # 获取缓存实例并清空
    cache = get_cache()
    deleted = cache.clear()  # 清空缓存，返回删除的键数量

    return {
        "message": "缓存已清空",
        "deleted_keys": deleted,  # 删除的键数量
    }


@app.get("/api/v1/cache/stats")
async def cache_stats():
    """
    缓存统计
    
    功能说明：
        获取缓存的统计信息（命中率、键数量等）
    
    返回示例：
        {
            "hits": 1000,
            "misses": 200,
            "hit_rate": 0.833,
            "keys": 150,
            "size": "2.5 MB"
        }
    """
    # 检查缓存是否启用
    if not settings.CACHE_ENABLED:
        return {"message": "缓存未启用"}

    # 获取缓存统计
    cache = get_cache()
    return cache.stats()  # 返回统计信息


# ============================================================================
# 应用事件处理器（启动和关闭）
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    应用启动事件
    
    功能说明：
        应用启动时执行的初始化操作
        注意：这是旧版 FastAPI 的事件处理方式
        新版推荐使用 lifespan（已在上面定义）
    
    工作流程：
        1. 打印启动信息
        2. 连接数据库
        3. 初始化服务
    """
    logger.info("启动 AI Chat App - RAG Service v2.0.0")

    # 连接数据库
    try:
        db = get_database()  # 获取数据库实例
        await db.connect()  # 建立连接
        logger.info("数据库连接成功")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        # 不要抛出异常，允许服务启动但标记数据库不可用
        # 这样可以让健康检查端点正常工作


@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭事件
    
    功能说明：
        应用关闭时执行的清理操作
        注意：这是旧版 FastAPI 的事件处理方式
        新版推荐使用 lifespan（已在上面定义）
    
    工作流程：
        1. 打印关闭信息
        2. 断开数据库连接
        3. 清理资源
    """
    logger.info("关闭 AI Chat App - RAG Service")

    # 断开数据库
    try:
        db = get_database()  # 获取数据库实例
        await db.disconnect()  # 断开连接
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"数据库断开失败: {e}")


# ============================================================================
# 主程序入口（直接运行时）
# ============================================================================

if __name__ == "__main__":
    """
    主程序入口
    
    功能说明：
        当直接运行此文件时（python app/main.py），启动 Uvicorn 服务器
    
    运行方式：
        1. 开发模式（自动重载）：
           python app/main.py
        
        2. 生产模式（手动启动）：
           uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
    
    参数说明：
        - app.main:app: 应用路径（模块:变量）
        - host: 监听地址（0.0.0.0 表示所有网卡）
        - port: 监听端口
        - reload: 是否自动重载（开发模式启用）
    """
    import uvicorn  # ASGI 服务器

    # 启动 Uvicorn 服务器
    uvicorn.run(
        "app.main:app",  # FastAPI 应用路径
        host=settings.HOST,  # 监听地址（从配置读取）
        port=settings.PORT,  # 监听端口（从配置读取）
        reload=settings.DEBUG,  # 自动重载（开发模式启用）
    )
