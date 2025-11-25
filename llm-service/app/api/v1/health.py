"""
============================================================================
健康检查 API
============================================================================

文件位置：
  llm-service/app/api/v1/health.py

文件作用：
  提供服务健康检查接口，用于监控和容器编排

主要功能：
  1. 健康检查 - 返回服务状态和配置信息
  2. 存活探针 - Kubernetes Liveness Probe
  3. 就绪探针 - Kubernetes Readiness Probe

技术栈：
  - FastAPI（Web 框架）
  - Kubernetes Probes（容器健康检查）

路由：
  - GET /health       完整健康检查
  - GET /health/live  存活探针（检测服务是否崩溃）
  - GET /health/ready 就绪探针（检测服务是否可接受流量）

使用场景：
  - Docker Compose healthcheck
  - Kubernetes liveness/readiness probes
  - 监控系统（Prometheus、Grafana）
  - 负载均衡器健康检查

依赖文件：
  - app/core/config.py          配置管理
  - app/models/responses.py     响应模型定义

============================================================================
"""
from fastapi import APIRouter  # FastAPI 路由器
import time  # 时间模块（用于计算运行时长）
from app.core.config import settings  # 应用配置（从环境变量加载）
from app.models.responses import HealthResponse  # 健康检查响应模型

# ============================================================================
# 路由器初始化
# ============================================================================
router = APIRouter()  # 创建 FastAPI 路由器实例

# ============================================================================
# 全局变量：服务启动时间
# ============================================================================
# 服务启动时间（Unix 时间戳）
# 用于计算服务运行时长（uptime）
START_TIME = time.time()

# ============================================================================
# API 端点 1：完整健康检查
# ============================================================================
@router.get("/health", response_model=HealthResponse)  # 路由：GET /api/v1/health
async def health_check():
    """
    健康检查
    返回服务状态和基本信息
    
    功能说明：
      - 检查服务是否正常运行
      - 返回版本号、环境、配置状态
      - 用于监控系统和负载均衡器
    
    返回：
      HealthResponse: 包含以下字段
        - status: 服务状态（"healthy" / "unhealthy"）
        - version: 应用版本号（从配置读取）
        - environment: 运行环境（dev / staging / production）
        - providers: 外部服务配置状态
          - openrouter: OpenRouter API Key 是否配置
    
    使用示例：
      curl http://localhost:8002/api/v1/health
    
    响应示例：
      {
        "status": "healthy",
        "version": "1.0.0",
        "environment": "production",
        "providers": {
          "openrouter": true
        }
      }
    """
    return HealthResponse(
        status="healthy",  # 服务状态（固定返回 healthy，如需检测可添加逻辑）
        version=settings.APP_VERSION,  # 应用版本号（从 .env 读取）
        environment=settings.ENVIRONMENT,  # 运行环境（dev/staging/production）
        providers={
            # 检查 OpenRouter API Key 是否配置
            # bool() 将字符串转为布尔值（空字符串 = False）
            "openrouter": bool(settings.OPENROUTER_API_KEY)
        }
    )

# ============================================================================
# API 端点 2：存活探针（Liveness Probe）
# ============================================================================
@router.get("/health/live")  # 路由：GET /api/v1/health/live
async def liveness_probe():
    """
    存活探针
    用于 Kubernetes Liveness Probe
    
    功能说明：
      - 检测服务进程是否存活（未崩溃、未死锁）
      - 如果此接口无响应，Kubernetes 会重启容器
      - 轻量级检查，不检测依赖服务
    
    返回：
      {"status": "alive"}
    
    Kubernetes 配置示例：
      livenessProbe:
        httpGet:
          path: /api/v1/health/live
          port: 8002
        initialDelaySeconds: 30  # 启动后 30 秒开始检查
        periodSeconds: 10        # 每 10 秒检查一次
        timeoutSeconds: 5        # 超时时间 5 秒
        failureThreshold: 3      # 失败 3 次后重启
    
    使用场景：
      - 检测服务是否陷入死循环
      - 检测服务是否因内存泄漏而无响应
      - 检测服务是否因异常而崩溃
    """
    return {"status": "alive"}  # 简单返回，表示进程存活

# ============================================================================
# API 端点 3：就绪探针（Readiness Probe）
# ============================================================================
@router.get("/health/ready")  # 路由：GET /api/v1/health/ready
async def readiness_probe():
    """
    就绪探针
    用于 Kubernetes Readiness Probe
    
    功能说明：
      - 检测服务是否准备好接收流量
      - 如果此接口返回失败，Kubernetes 会将容器从负载均衡中移除
      - 可以检测依赖服务（数据库、缓存等）是否可用
    
    返回：
      {
        "status": "ready",
        "uptime": 服务运行时长（秒）
      }
    
    Kubernetes 配置示例：
      readinessProbe:
        httpGet:
          path: /api/v1/health/ready
          port: 8002
        initialDelaySeconds: 10  # 启动后 10 秒开始检查
        periodSeconds: 5         # 每 5 秒检查一次
        timeoutSeconds: 3        # 超时时间 3 秒
        failureThreshold: 3      # 失败 3 次后移除流量
    
    使用场景：
      - 服务启动后需要预热（加载模型、连接数据库）
      - 依赖服务不可用时暂时不接收流量
      - 滚动更新时平滑切换流量
    
    扩展建议：
      可以添加以下检查：
        - 数据库连接状态
        - Redis 连接状态
        - OpenRouter API 可用性
        - 模型加载状态
    """
    return {
        "status": "ready",  # 就绪状态
        # 计算服务运行时长（当前时间 - 启动时间）
        "uptime": time.time() - START_TIME
    }
