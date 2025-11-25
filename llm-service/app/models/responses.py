"""
============================================================================
响应数据模型
============================================================================

文件位置：
  llm-service/app/models/responses.py

文件作用：
  定义 API 响应的数据模型，统一响应格式

主要功能：
  1. 统一响应结构 - 所有接口返回相同的数据格式
  2. 类型验证 - 使用 Pydantic 自动验证响应数据
  3. 文档生成 - 自动生成 Swagger 文档示例

响应模型：
  - BaseResponse: 基础响应（通用）
  - GenerateResponse: 生成响应（LLM 生成接口）
  - HealthResponse: 健康检查响应（监控接口）

响应格式：
  {
      "success": true,
      "message": "操作成功",
      "data": {...}
  }

技术栈：
  - Pydantic（数据验证）
  - Python Type Hints（类型注解）

使用场景：
  - API 接口返回值
  - 错误信息返回
  - 健康检查返回

依赖文件：
  - app/api/v1/generate.py（生成接口）
  - app/api/v1/health.py（健康检查接口）

============================================================================
"""
from pydantic import BaseModel, Field  # Pydantic 数据验证
from typing import Any, Optional, Dict  # 类型注解

# ============================================================================
# 基础响应模型
# ============================================================================

class BaseResponse(BaseModel):
    """
    基础响应模型
    
    所有 API 响应的基类，提供统一的响应格式
    
    功能说明：
      - 统一响应结构（success + message + data）
      - 便于前端统一处理响应
      - 便于错误处理和日志记录
    
    字段说明：
      - success: 操作是否成功（true/false）
      - message: 提示信息（成功/失败原因）
      - data: 响应数据（可选，根据接口而定）
    
    使用示例：
        # 成功响应
        BaseResponse(
            success=True,
            message="操作成功",
            data={"result": "..."}
        )
        
        # 失败响应
        BaseResponse(
            success=False,
            message="参数错误",
            data=None
        )
    """
    success: bool = Field(..., description="是否成功")  # 操作是否成功（必填）
    # success 说明：
    #   - True: 操作成功
    #   - False: 操作失败
    
    message: Optional[str] = Field(default=None, description="消息")  # 提示信息（可选）
    # message 说明：
    #   - 成功时：如 "生成成功"、"查询成功"
    #   - 失败时：如 "参数错误"、"模型不可用"
    
    data: Optional[Any] = Field(default=None, description="数据")  # 响应数据（可选）
    # data 说明：
    #   - 可以是任意类型（字典、列表、字符串等）
    #   - 根据具体接口定义数据结构


# ============================================================================
# 生成响应模型
# ============================================================================

class GenerateResponse(BaseResponse):
    """
    生成响应模型
    
    用于 LLM 生成接口的响应（非流式）
    
    功能说明：
      - 继承 BaseResponse 的基础字段
      - 重写 data 字段，指定为字典类型
      - 包含生成结果、模型信息、token 使用量等
    
    响应结构：
        {
            "success": true,
            "message": "生成成功",
            "data": {
                "response": "AI 生成的回复内容",
                "model": "openai/gpt-4o",
                "provider": "openrouter",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        }
    
    使用场景：
      - POST /api/v1/generate（非流式生成）
    """
    data: Optional[Dict[str, Any]] = Field(
        default=None,  # 默认值为 None（可选）
        description="响应数据"
    )
    # data 字段说明：
    #   - response: AI 生成的回复内容
    #   - model: 使用的模型名称
    #   - provider: LLM 提供商（如 openrouter）
    #   - usage: token 使用统计
    #       - prompt_tokens: 输入 token 数
    #       - completion_tokens: 输出 token 数
    #       - total_tokens: 总 token 数

    class Config:
        # Swagger 文档示例
        json_schema_extra = {
            "example": {
                "success": True,  # 操作成功
                "message": "生成成功",  # 提示信息
                "data": {
                    "response": "你好！我是 AI 助手...",  # AI 生成的回复
                    "model": "openai/gpt-4o",  # 使用的模型
                    "provider": "openrouter",  # LLM 提供商
                    "usage": {  # token 使用统计
                        "prompt_tokens": 10,  # 输入 token 数
                        "completion_tokens": 20,  # 输出 token 数
                        "total_tokens": 30  # 总 token 数
                    }
                }
            }
        }


# ============================================================================
# 健康检查响应模型
# ============================================================================

class HealthResponse(BaseModel):
    """
    健康检查响应模型
    
    用于健康检查接口的响应
    
    功能说明：
      - 返回服务状态信息
      - 返回版本和环境信息
      - 返回依赖服务的可用性
    
    响应结构：
        {
            "status": "healthy",
            "version": "1.0.0",
            "environment": "production",
            "providers": {
                "openrouter": true
            }
        }
    
    使用场景：
      - GET /api/v1/health（完整健康检查）
      - GET /api/v1/health/live（存活探针）
      - GET /api/v1/health/ready（就绪探针）
    """
    status: str = Field(..., description="服务状态")  # 服务状态（必填）
    # status 说明：
    #   - "healthy": 服务正常
    #   - "unhealthy": 服务异常
    #   - "degraded": 服务降级（部分功能不可用）
    
    version: str = Field(..., description="版本号")  # 应用版本号（必填）
    # version 说明：
    #   - 格式：主版本.次版本.修订版本（如 1.0.0）
    #   - 用于版本追踪和问题排查
    
    environment: str = Field(..., description="运行环境")  # 运行环境（必填）
    # environment 说明：
    #   - "development": 开发环境
    #   - "staging": 预发布环境
    #   - "production": 生产环境
    
    providers: Dict[str, bool] = Field(..., description="可用的 LLM 提供商")  # LLM 提供商可用性（必填）
    # providers 说明：
    #   - 键：提供商名称（如 "openrouter"）
    #   - 值：是否可用（true/false）
    #   - 示例：{"openrouter": true, "anthropic": false}


# ============================================================================
# 使用示例
# ============================================================================
# 示例 1：成功响应
# response = GenerateResponse(
#     success=True,
#     message="生成成功",
#     data={
#         "response": "你好！我是 AI 助手...",
#         "model": "openai/gpt-4o",
#         "provider": "openrouter",
#         "usage": {
#             "prompt_tokens": 10,
#             "completion_tokens": 20,
#             "total_tokens": 30
#         }
#     }
# )

# 示例 2：失败响应
# response = BaseResponse(
#     success=False,
#     message="模型不可用",
#     data=None
# )

# 示例 3：健康检查响应
# response = HealthResponse(
#     status="healthy",
#     version="1.0.0",
#     environment="production",
#     providers={"openrouter": True}
# )

# ============================================================================
# 响应格式说明
# ============================================================================
# 统一响应格式的优势：
#   1. 前端统一处理：通过 success 字段判断成功/失败
#   2. 错误处理简单：失败时 message 包含错误原因
#   3. 数据结构清晰：data 字段包含实际数据
#   4. 便于日志记录：统一的结构便于日志分析
#   5. API 文档友好：Swagger 自动生成文档

# 前端处理示例（JavaScript）：
# fetch('/api/v1/generate', {
#     method: 'POST',
#     body: JSON.stringify(request)
# })
# .then(res => res.json())
# .then(data => {
#     if (data.success) {
#         console.log('成功:', data.data);
#     } else {
#         console.error('失败:', data.message);
#     }
# });

# ============================================================================
# 流式响应说明
# ============================================================================
# 注意：流式响应（/api/v1/generate/stream）不使用此模型
# 流式响应使用 Server-Sent Events 格式：
#   data: {"type": "content", "content": "文本片段"}\n\n
#   data: {"type": "done", "usage": {...}}\n\n
#   data: [DONE]\n\n
