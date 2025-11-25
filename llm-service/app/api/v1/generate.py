"""
============================================================================
生成 API - OpenRouter 版本
============================================================================

文件位置：
  llm-service/app/api/v1/generate.py

文件作用：
  LLM 服务的核心 API 路由，提供文本生成功能

主要功能：
  1. 流式生成（SSE）- 实时返回生成内容
  2. 普通生成 - 一次性返回完整内容
  3. 模型列表查询
  4. 模型信息查询

技术栈：
  - FastAPI（Web 框架）
  - OpenRouter（LLM 提供商）
  - Server-Sent Events（流式传输）

路由：
  - POST /stream          流式生成
  - POST /                普通生成
  - GET  /models          获取模型列表
  - GET  /models/{model}  获取模型信息

============================================================================
"""
from fastapi import APIRouter, HTTPException  # FastAPI 路由和异常处理
from fastapi.responses import StreamingResponse  # 流式响应类
import traceback  # 异常堆栈追踪
from app.models.requests import GenerateRequest  # 请求模型（定义请求参数结构）
from app.models.responses import GenerateResponse  # 响应模型（定义响应数据结构）
from app.services.llm_service import LLMService  # LLM 服务（封装 OpenRouter 调用逻辑）
from app.core.logger import logger  # 日志记录器

# ============================================================================
# 路由器初始化
# ============================================================================
router = APIRouter()  # 创建 FastAPI 路由器实例，用于注册 API 端点

# ============================================================================
# 服务实例创建
# ============================================================================
# 创建 LLM 服务实例（单例模式，全局共享）
# 负责与 OpenRouter API 交互，处理模型调用、流式传输等
llm_service = LLMService()

# ============================================================================
# API 端点 1：流式生成
# ============================================================================
@router.post("/stream")  # 路由装饰器：POST 请求，路径 /api/v1/generate/stream
async def generate_stream(request: GenerateRequest):
    """
    流式生成 API
    使用 Server-Sent Events (SSE) 返回流式响应
    
    功能说明：
      - 接收用户消息，调用 LLM 生成回复
      - 以流式方式返回内容（类似打字机效果）
      - 适用于聊天场景，提升用户体验
    
    参数：
      request (GenerateRequest): 包含以下字段
        - messages: 消息列表 [{"role": "user", "content": "..."}]
        - model: 模型名称（如 "openai/gpt-4"）
        - temperature: 温度参数（0-1，控制随机性）
        - max_tokens: 最大生成长度
    
    返回：
      StreamingResponse: SSE 流式响应
        - 格式：data: {"content": "文本片段"}\n\n
        - 结束标志：data: [DONE]\n\n
    
    异常：
      HTTPException 500: 生成失败
    """
    try:
        # 记录请求信息（用于调试和监控）
        logger.info(f"收到流式生成请求")
        logger.info(f"  模型: {request.model}")  # 记录使用的模型
        logger.info(f"  消息数: {len(request.messages)}")  # 记录消息条数

        # 调用 LLM 服务生成内容
        # msg.model_dump() 将 Pydantic 模型转为字典
        result = await llm_service.generate(
            messages=[msg.model_dump() for msg in request.messages],  # 转换消息格式
            model=request.model,  # 指定模型
            temperature=request.temperature,  # 温度参数
            max_tokens=request.max_tokens,  # 最大 token 数
            stream=True  # 启用流式传输
        )

        # 返回流式响应
        # result 是一个异步生成器，会逐块返回数据
        return StreamingResponse(
            result,  # 异步生成器（yield 数据块）
            media_type="text/event-stream",  # SSE 标准 MIME 类型
            headers={
                "Cache-Control": "no-cache",  # 禁止缓存（确保实时性）
                "Connection": "keep-alive",  # 保持连接（长连接）
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲（立即发送数据）
            }
        )
    except Exception as e:
        # 异常处理：记录错误并返回 HTTP 500
        logger.error(f"流式生成失败: {e}")
        logger.error(f"错误详情: {traceback.format_exc()}")  # 记录完整堆栈
        raise HTTPException(
            status_code=500,  # HTTP 500 内部服务器错误
            detail=f"流式生成失败: {str(e)}"  # 错误详情
        )

# ============================================================================
# API 端点 2：普通生成（非流式）
# ============================================================================
@router.post("", response_model=GenerateResponse)  # 路由：POST /api/v1/generate
async def generate(request: GenerateRequest):
    """
    普通生成 API（非流式）
    
    功能说明：
      - 一次性返回完整生成内容
      - 适用于不需要实时反馈的场景
    
    参数：
      request (GenerateRequest): 同流式接口
    
    返回：
      GenerateResponse: 包含以下字段
        - success: 是否成功
        - message: 提示信息
        - data: 生成结果（完整文本）
    
    异常：
      HTTPException 500: 生成失败
    """
    try:
        # 记录请求信息
        logger.info(f"收到生成请求")
        logger.info(f"  模型: {request.model}")
        logger.info(f"  消息数: {len(request.messages)}")

        # 调用 LLM 服务（非流式）
        result = await llm_service.generate(
            messages=[msg.model_dump() for msg in request.messages],
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False  # 关闭流式传输
        )

        # 记录成功日志
        logger.info("生成成功")
        
        # 返回标准响应格式
        return GenerateResponse(
            success=True,  # 成功标志
            message="生成成功",  # 提示信息
            data=result  # 生成结果（字典，包含 content 等字段）
        )
    except Exception as e:
        # 异常处理
        logger.error(f"生成失败: {e}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"生成失败: {str(e)}"
        )

# ============================================================================
# API 端点 3：获取可用模型列表
# ============================================================================
@router.get("/models")  # 路由：GET /api/v1/generate/models
async def list_models():
    """
    获取可用模型列表
    
    功能说明：
      - 查询 OpenRouter 支持的所有模型
      - 返回模型名称、提供商、定价等信息
    
    返回：
      {
        "success": true,
        "data": {
          "models": [
            {
              "id": "openai/gpt-4",
              "name": "GPT-4",
              "provider": "OpenAI",
              ...
            }
          ],
          "count": 模型数量
        }
      }
    
    异常：
      HTTPException 500: 查询失败
    """
    try:
        # 调用服务层获取模型列表
        models = await llm_service.list_models()
        
        # 返回标准格式
        return {
            "success": True,
            "data": {
                "models": models,  # 模型列表（数组）
                "count": len(models)  # 模型总数
            }
        }
    except Exception as e:
        # 异常处理
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取模型列表失败: {str(e)}"
        )

# ============================================================================
# API 端点 4：获取单个模型信息
# ============================================================================
@router.get("/models/{model}")  # 路由：GET /api/v1/generate/models/openai/gpt-4
async def get_model_info(model: str):
    """
    获取模型信息
    
    功能说明：
      - 查询指定模型的详细信息
      - 包括定价、上下文长度、能力等
    
    参数：
      model (str): 模型 ID（如 "openai/gpt-4"）
    
    返回：
      {
        "success": true,
        "data": {
          "id": "openai/gpt-4",
          "name": "GPT-4",
          "context_length": 8192,
          "pricing": {...},
          ...
        }
      }
    
    异常：
      HTTPException 500: 查询失败
    """
    try:
        # 调用服务层获取模型信息
        info = llm_service.get_model_info(model)
        
        # 返回标准格式
        return {
            "success": True,
            "data": info  # 模型详细信息（字典）
        }
    except Exception as e:
        # 异常处理
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取模型信息失败: {str(e)}"
        )
