"""
============================================================================
FastAPI 应用入口
============================================================================

文件位置：
  llm-service/app/main.py

文件作用：
  FastAPI 应用的主入口文件，负责应用初始化和配置

主要功能：
  1. 应用创建 - 创建 FastAPI 应用实例
  2. 生命周期管理 - 启动和关闭时的初始化/清理
  3. 中间件配置 - CORS、Gzip、请求日志等
  4. 路由注册 - 注册所有 API 路由
  5. 异常处理 - 全局异常捕获和处理
  6. 健康检查 - 服务状态监控

应用结构：
  FastAPI 应用
    ├── 生命周期管理（启动/关闭）
    ├── 中间件（CORS、Gzip、日志）
    ├── 路由（生成、搜索、健康检查）
    └── 异常处理（全局异常捕获）

技术栈：
  - FastAPI（Web 框架）
  - Uvicorn（ASGI 服务器）
  - Pydantic（数据验证）

访问地址：
  - 服务地址: http://localhost:8002
  - API 文档: http://localhost:8002/docs
  - 健康检查: http://localhost:8002/health

依赖文件：
  - app/core/config.py（配置管理）
  - app/core/logger.py（日志记录）
  - app/api/v1/router.py（API 路由）
  - app/api/v1/search.py（搜索路由）

============================================================================
"""
from fastapi import FastAPI, Request  # FastAPI 框架和请求对象
from fastapi.middleware.cors import CORSMiddleware  # CORS 中间件（跨域支持）
from fastapi.middleware.gzip import GZipMiddleware  # Gzip 压缩中间件
from fastapi.responses import JSONResponse  # JSON 响应
from contextlib import asynccontextmanager  # 异步上下文管理器（用于生命周期管理）
import time  # 时间模块（用于计算请求耗时）
from app.core.config import settings  # 应用配置
from app.api.v1.router import api_router  # API 路由（生成、模型等）
from app.core.logger import logger  # 日志记录器
from app.api.v1 import search  # 搜索路由（博查 AI 搜索）


# ============================================================================
# 生命周期管理
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    功能说明：
      - 在应用启动时执行初始化操作
      - 在应用关闭时执行清理操作
      - 使用异步上下文管理器（async with）
    
    生命周期：
      1. 启动前：yield 之前的代码
      2. 运行中：应用正常运行
      3. 关闭后：yield 之后的代码
    
    Args:
        app: FastAPI 应用实例
    
    使用示例：
        app = FastAPI(lifespan=lifespan)
    """
    # ========== 启动时 ==========
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"环境: {settings.ENVIRONMENT}")  # 环境（development/production）
    logger.info(f"调试模式: {settings.DEBUG}")  # 是否启用调试模式
    logger.info(f"监听地址: {settings.HOST}:{settings.PORT}")  # 监听地址和端口
    logger.info(f"Bocha API Key: {'已配置' if settings.BOCHA_API_KEY else ' 未配置'}")  # 博查 API Key 状态
    logger.info("=" * 60)

    yield  # 应用运行中（yield 之前是启动，之后是关闭）

    # ========== 关闭时 ==========
    logger.info("=" * 60)
    logger.info(f" {settings.APP_NAME} 关闭中...")
    logger.info("=" * 60)


# ============================================================================
# 创建应用
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,  # 应用名称（显示在 API 文档中）
    description="LLM Service - 支持多个 LLM 提供商的统一接口 + 联网搜索功能",  # 应用描述
    version=settings.APP_VERSION,  # 应用版本号
    docs_url="/docs" if settings.DEBUG else None,  # Swagger 文档地址（仅调试模式）
    redoc_url="/redoc" if settings.DEBUG else None,  # ReDoc 文档地址（仅调试模式）
    lifespan=lifespan,  # 生命周期管理函数
)
# 说明：
#   - docs_url: Swagger UI 文档地址（交互式 API 文档）
#   - redoc_url: ReDoc 文档地址（美观的 API 文档）
#   - 生产环境禁用文档（安全考虑）


# ============================================================================
# 中间件配置
# ============================================================================

# ========== CORS 中间件 ==========
# 功能：允许跨域请求（前后端分离必备）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # 允许的源（如 ["http://localhost:3000"]）
    allow_credentials=True,  # 允许携带 Cookie
    allow_methods=["*"],  # 允许所有 HTTP 方法（GET、POST、PUT、DELETE 等）
    allow_headers=["*"],  # 允许所有请求头
)
# CORS 说明：
#   - allow_origins: 允许的前端地址列表
#   - allow_credentials: 是否允许携带认证信息（Cookie、Authorization）
#   - allow_methods: 允许的 HTTP 方法
#   - allow_headers: 允许的请求头

# ========== Gzip 压缩中间件 ==========
# 功能：自动压缩响应体，减少网络传输量
app.add_middleware(GZipMiddleware, minimum_size=1000)
# 说明：
#   - minimum_size: 最小压缩大小（小于 1000 字节不压缩）
#   - 压缩比：通常可达 70%-90%
#   - 适用场景：JSON、HTML、CSS、JavaScript 等文本内容


# ========== 请求日志中间件 ==========
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    记录所有请求
    
    功能说明：
      - 记录请求的方法和路径
      - 记录响应状态码和耗时
      - 在响应头中添加处理时间
    
    Args:
        request: 请求对象
        call_next: 下一个中间件/路由处理函数
    
    Returns:
        响应对象（添加了 X-Process-Time 响应头）
    
    日志示例：
         POST /api/v1/generate
         POST /api/v1/generate - 200 - 1.234s
    """
    # ========== 1. 记录请求开始 ==========
    start_time = time.time()  # 记录开始时间
    logger.info(f" {request.method} {request.url.path}")  # 记录请求方法和路径

    # ========== 2. 处理请求 ==========
    response = await call_next(request)  # 调用下一个中间件/路由处理函数

    # ========== 3. 记录请求结束 ==========
    duration = time.time() - start_time  # 计算耗时
    logger.info(
        f" {request.method} {request.url.path} "
        f"- {response.status_code} "  # 响应状态码
        f"- {duration:.3f}s"  # 耗时（保留 3 位小数）
    )

    # ========== 4. 添加响应头 ==========
    response.headers["X-Process-Time"] = str(duration)  # 在响应头中添加处理时间
    return response


# ============================================================================
# 异常处理
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理
    
    功能说明：
      - 捕获所有未处理的异常
      - 记录详细的错误日志
      - 返回统一的错误响应
    
    Args:
        request: 请求对象
        exc: 异常对象
    
    Returns:
        JSON 错误响应：
        {
            "success": false,
            "error": "Internal server error",
            "detail": "错误详情",
            "type": "异常类型"
        }
    
    使用场景：
      - 未预期的异常（如数据库连接失败）
      - 第三方 API 调用失败
      - 代码逻辑错误
    """
    import traceback  # 导入 traceback 模块（用于获取完整堆栈）
    
    # ========== 1. 记录错误日志 ==========
    logger.error(f"未处理的异常: {exc}")  # 记录异常信息
    logger.error(f"错误详情: {traceback.format_exc()}")  # 记录完整堆栈
    logger.error(f"请求路径: {request.url.path}")  # 记录请求路径
    logger.error(f"请求方法: {request.method}")  # 记录请求方法

    # ========== 2. 返回错误响应 ==========
    return JSONResponse(
        status_code=500,  # HTTP 状态码：500 Internal Server Error
        content={
            "success": False,  # 操作失败
            "error": "Internal server error",  # 错误类型
            "detail": str(exc) if settings.DEBUG else "服务器内部错误",  # 错误详情（调试模式显示详细信息）
            "type": type(exc).__name__  # 异常类型（如 ValueError、KeyError）
        }
    )
    # 说明：
    #   - 调试模式：返回详细错误信息（便于开发调试）
    #   - 生产模式：返回通用错误信息（避免泄露敏感信息）


# ============================================================================
# 路由注册
# ============================================================================

# ========== 注册 API 路由 ==========
# 包含：生成接口、模型列表、健康检查等
app.include_router(api_router, prefix="/api/v1")
# 说明：
#   - api_router: 主 API 路由（定义在 app/api/v1/router.py）
#   - prefix: 路由前缀（所有路由都以 /api/v1 开头）
#   - 示例：/api/v1/generate、/api/v1/models
# ========== 注册搜索路由 ==========
# 包含：博查 AI 搜索接口
app.include_router(
    search.router,  # 搜索路由（定义在 app/api/v1/search.py）
    prefix="/api/v1",  # 路由前缀
    tags=["Search"]  # 标签（在 API 文档中分组显示）
)
# 说明：
#   - search.router: 搜索路由
#   - tags: 在 Swagger 文档中的分组标签


# ============================================================================
# 根路径
# ============================================================================

@app.get("/")
async def root():
    """
    根路径
    
    功能说明：
      - 返回服务基本信息
      - 显示可用功能列表
      - 提供 API 文档地址
    
    Returns:
        服务信息字典：
        {
            "service": "LLM Service",
            "version": "1.0.0",
            "environment": "development",
            "docs": "/docs",
            "status": "running",
            "features": {
                "generate": true,
                "search": true
            }
        }
    
    访问地址：
        http://localhost:8002/
    """
    return {
        "service": settings.APP_NAME,  # 服务名称
        "version": settings.APP_VERSION,  # 版本号
        "environment": settings.ENVIRONMENT,  # 运行环境
        "docs": "/docs" if settings.DEBUG else "disabled",  # API 文档地址（仅调试模式）
        "status": "running",  # 服务状态
        "features": {  # 可用功能列表
            "generate": True,  # 生成功能（始终可用）
            "search": bool(settings.BOCHA_API_KEY)  # 搜索功能（需要配置博查 API Key）
        }
    }


# ============================================================================
# 健康检查接口（增强版）
# ============================================================================

@app.get("/health")
async def health_check():
    """
    健康检查
    
    功能说明：
      - 检查服务是否正常运行
      - 检查各个功能模块的可用性
      - 检查依赖服务的连接状态
    
    Returns:
        健康状态字典：
        {
            "status": "healthy",
            "service": "LLM Service",
            "version": "1.0.0",
            "environment": "development",
            "features": {
                "generate": {
                    "enabled": true,
                    "providers": {
                        "openrouter": true,
                        "bocha": true
                    }
                },
                "search": {
                    "enabled": true,
                    "provider": "bocha"
                }
            }
        }
    
    访问地址：
        http://localhost:8002/health
    
    使用场景：
      - Kubernetes 健康探针（liveness/readiness）
      - 监控系统（如 Prometheus）
      - 负载均衡器健康检查
    """
    return {
        "status": "healthy",  # 服务状态（healthy/unhealthy）
        "service": settings.APP_NAME,  # 服务名称
        "version": settings.APP_VERSION,  # 版本号
        "environment": settings.ENVIRONMENT,  # 运行环境
        # 检查各个功能模块的可用性
        "features": {
            "generate": {  # 生成功能
                "enabled": True,  # 是否启用
                "providers": {  # 提供商可用性
                    "openrouter": bool(settings.OPENROUTER_API_KEY),  # 正确：OpenRouter 可用性
                    "bocha": bool(settings.BOCHA_API_KEY)  # 添加博查检查
                }
            },
            "search": {  # 搜索功能
                "enabled": bool(settings.BOCHA_API_KEY),  # 是否启用（需要博查 API Key）
                "provider": "bocha"  # 提供商名称
            }
        }
    }
    # 说明：
    #   - status: 服务整体状态
    #   - features: 各个功能模块的详细状态
    #   - providers: 各个提供商的可用性


# ============================================================================
# 应用启动
# ============================================================================

if __name__ == "__main__":
    """
    直接运行脚本时启动应用
    
    功能说明：
      - 使用 Uvicorn ASGI 服务器运行应用
      - 支持热重载（调试模式）
      - 配置监听地址和端口
    
    启动命令：
        python app/main.py
    
    生产环境启动：
        uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 4
    """
    import uvicorn  # 导入 Uvicorn ASGI 服务器

    uvicorn.run(
        "app.main:app",  # 应用路径（模块:变量）
        host=settings.HOST,  # 监听地址（0.0.0.0 表示所有网卡）
        port=settings.PORT,  # 监听端口（默认 8002）
        reload=settings.DEBUG,  # 热重载（调试模式启用，代码修改自动重启）
        log_level=settings.LOG_LEVEL.lower(),  # 日志级别（INFO、DEBUG、WARNING、ERROR）
    )
    # 说明：
    #   - reload: 热重载（仅开发环境，生产环境禁用）
    #   - workers: 工作进程数（生产环境建议设置为 CPU 核心数）
    #   - log_level: 日志级别（控制输出的日志详细程度）


# ============================================================================
# 中间件执行顺序
# ============================================================================
# 请求流程：
#   1. CORS 中间件（处理跨域）
#   2. Gzip 中间件（压缩响应）
#   3. 请求日志中间件（记录日志）
#   4. 路由处理（执行业务逻辑）
#   5. 异常处理（捕获异常）
#
# 响应流程：
#   5. 异常处理（如果有异常）
#   4. 路由处理（返回响应）
#   3. 请求日志中间件（记录日志）
#   2. Gzip 中间件（压缩响应）
#   1. CORS 中间件（添加 CORS 头）

# ============================================================================
# API 文档访问
# ============================================================================
# Swagger UI（交互式文档）：
#   http://localhost:8002/docs
#
# ReDoc（美观文档）：
#   http://localhost:8002/redoc
#
# OpenAPI JSON：
#   http://localhost:8002/openapi.json

# ============================================================================
# 生产环境部署建议
# ============================================================================
# 1. 使用多个工作进程：
#    uvicorn app.main:app --workers 4
#
# 2. 使用进程管理器（如 Supervisor、systemd）：
#    [program:llm-service]
#    command=uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 4
#
# 3. 使用反向代理（如 Nginx）：
#    location /api/ {
#        proxy_pass http://localhost:8002;
#    }
#
# 4. 启用 HTTPS（使用 Let's Encrypt）
#
# 5. 配置日志轮转（使用 logrotate）
#
# 6. 配置监控（如 Prometheus + Grafana）
