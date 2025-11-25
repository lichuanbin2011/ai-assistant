"""
============================================================================
API 路由聚合
============================================================================

文件位置：
  llm-service/app/api/v1/router.py

文件作用：
  聚合所有 v1 版本的 API 路由，统一管理路由结构

主要功能：
  1. 创建 v1 版本的主路由器
  2. 注册各个子模块的路由
  3. 配置路由前缀和标签

路由结构：
  /api/v1
    ├── /generate          生成相关接口（来自 generate.py）
    │   ├── POST /stream   流式生成
    │   ├── POST /         普通生成
    │   └── GET /models    模型列表
    └── /health            健康检查接口（来自 health.py）
        ├── GET /health    完整健康检查
        ├── GET /health/live   存活探针
        └── GET /health/ready  就绪探针

技术栈：
  - FastAPI APIRouter（模块化路由管理）

设计模式：
  - 路由分层：主路由 → 子路由 → 端点
  - 关注点分离：每个功能模块独立文件
  - 易于扩展：新增功能只需添加 include_router

依赖文件：
  - app/api/v1/generate.py  生成 API 路由
  - app/api/v1/health.py    健康检查路由

使用位置：
  - app/main.py 会引入此路由器并挂载到 /api/v1

============================================================================
"""
from fastapi import APIRouter  # FastAPI 路由器（用于模块化路由管理）
from app.api.v1 import generate, health  # 导入子路由模块

# ============================================================================
# 创建 v1 版本主路由器
# ============================================================================
# 创建 v1 路由器实例
# 此路由器会被挂载到 /api/v1 路径下（在 main.py 中配置）
api_router = APIRouter()

# ============================================================================
# 注册子路由 1：生成 API
# ============================================================================
# 注册生成相关的路由（来自 generate.py）
api_router.include_router(
    generate.router,  # 引入 generate.py 中定义的 router 对象
    prefix="/generate",  # 路由前缀：所有路由会添加 /generate 前缀
                         # 例如：/api/v1/generate/stream
    tags=["生成"]  # Swagger 文档标签（用于分组显示）
                   # 在 API 文档中会显示为 "生成" 分组
)
# 最终路由：
#   POST /api/v1/generate/stream    流式生成
#   POST /api/v1/generate           普通生成
#   GET  /api/v1/generate/models    获取模型列表
#   GET  /api/v1/generate/models/{model}  获取模型信息

# ============================================================================
# 注册子路由 2：健康检查 API
# ============================================================================
# 注册健康检查相关的路由（来自 health.py）
api_router.include_router(
    health.router,  # 引入 health.py 中定义的 router 对象
    tags=["健康检查"]  # Swagger 文档标签
                      # 在 API 文档中会显示为 "健康检查" 分组
)
# 注意：此处没有 prefix 参数
# 因为 health.py 中已经定义了完整路径（如 /health）
# 最终路由：
#   GET /api/v1/health        完整健康检查
#   GET /api/v1/health/live   存活探针
#   GET /api/v1/health/ready  就绪探针

# ============================================================================
# 扩展说明
# ============================================================================
# 如需添加新功能模块，按以下步骤操作：
#
# 1. 创建新文件：app/api/v1/new_feature.py
#    from fastapi import APIRouter
#    router = APIRouter()
#    
#    @router.get("/example")
#    async def example():
#        return {"message": "example"}
#
# 2. 在此文件导入：
#    from app.api.v1 import new_feature
#
# 3. 注册路由：
#    api_router.include_router(
#        new_feature.router,
#        prefix="/new-feature",
#        tags=["新功能"]
#    )
#
# 4. 访问路径：/api/v1/new-feature/example
# ============================================================================
