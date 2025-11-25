"""
============================================================================
联网搜索接口
支持博查 AI 搜索 + LLM 生成
============================================================================

文件位置：
  llm-service/app/api/v1/search.py

文件作用：
  提供联网搜索功能，结合博查 AI 搜索和 LLM 生成能力

主要功能：
  1. 联网搜索（非流式）- 一次性返回搜索结果和生成答案
  2. 联网搜索（流式）- 实时返回搜索过程和生成内容
  3. 搜索结果增强 - 将搜索结果作为上下文提供给 LLM

工作流程：
  用户提问 → 博查 AI 搜索 → 提取搜索结果 → 构建增强 Prompt 
  → LLM 生成答案 → 返回答案 + 来源引用

技术栈：
  - FastAPI（Web 框架）
  - 博查 AI（搜索引擎）
  - OpenRouter（LLM 提供商）
  - Server-Sent Events（流式传输）

路由：
  - POST /search        非流式搜索
  - POST /search/stream 流式搜索

依赖服务：
  - 博查 AI API（搜索服务）
  - OpenRouter API（LLM 服务）

依赖文件：
  - app/core/config.py              配置管理
  - app/services/bocha_client.py    博查 AI 客户端

============================================================================
"""
from fastapi import APIRouter, HTTPException  # FastAPI 路由和异常处理
from fastapi.responses import StreamingResponse  # 流式响应类
from pydantic import BaseModel, Field  # 数据验证模型
from typing import List, Dict, Optional, Any  # 类型注解
from datetime import datetime  # 日期时间处理
import json  # JSON 序列化
import time  # 时间计算
from loguru import logger  # 日志记录器

from app.core.config import settings  # 应用配置
from app.services.bocha_client import bocha_client  # 博查 AI 客户端
from openai import AsyncOpenAI  # OpenAI 异步客户端（兼容 OpenRouter）

# ============================================================================
# 路由器初始化
# ============================================================================
router = APIRouter()  # 创建 FastAPI 路由器实例

# ============================================================================
# OpenRouter 客户端初始化
# ============================================================================
# 初始化 OpenRouter 客户端（使用 OpenAI SDK 兼容接口）
openai_client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,  # 从配置读取 API Key
    base_url=settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"  # OpenRouter API 地址
)


# ============================================================================
# Pydantic 模型定义
# ============================================================================

class Message(BaseModel):
    """
    消息模型
    
    用于表示聊天历史中的单条消息
    """
    role: str = Field(..., description="角色：system/user/assistant")  # 消息角色
    content: str = Field(..., description="消息内容")  # 消息文本内容


class SearchRequest(BaseModel):
    """
    搜索请求模型
    
    定义搜索接口的请求参数结构和验证规则
    """
    query: str = Field(..., min_length=1, max_length=500, description="搜索关键词")  # 搜索查询（必填，1-500 字符）
    model: str = Field(settings.OPENROUTER_DEFAULT_MODEL, description="使用的模型")  # LLM 模型名称（默认值从配置读取）
    chat_history: Optional[List[Message]] = Field([], description="聊天历史")  # 历史对话（可选，用于多轮对话）
    stream: bool = Field(False, description="是否流式响应")  # 是否启用流式传输
    max_results: int = Field(10, ge=1, le=20, description="最大搜索结果数")  # 搜索结果数量（1-20）
    max_tokens: int = Field(2000, ge=1, le=4096, description="最大生成长度")  # LLM 生成的最大 token 数
    temperature: float = Field(0.7, ge=0, le=2, description="温度")  # 温度参数（控制随机性）

    class Config:
        # Swagger 文档示例
        json_schema_extra = {
            "example": {
                "query": "2024年AI最新进展",
                "model": "openai/gpt-4o",
                "stream": False,
                "max_results": 10
            }
        }


class SearchSource(BaseModel):
    """
    搜索来源模型
    
    表示单个搜索结果的元数据
    """
    title: str  # 网页标题
    url: str  # 网页 URL
    content: str  # 网页内容摘要
    publishedDate: Optional[str] = None  # 发布日期（可选）
    siteName: Optional[str] = None  # 网站名称（可选）


class SearchResponse(BaseModel):
    """
    搜索响应模型
    
    定义搜索接口的返回数据结构
    """
    answer: str = Field(..., description="生成的回答")  # LLM 生成的答案
    sources: List[SearchSource] = Field(..., description="搜索来源")  # 搜索结果来源列表
    search_results: List[Dict[str, Any]] = Field(..., description="原始搜索结果")  # 完整的原始搜索数据
    model: str = Field(..., description="使用的模型")  # 使用的 LLM 模型名称
    tokens_used: int = Field(..., description="消耗的 Token 数")  # LLM 消耗的 token 数量
    latency_ms: int = Field(..., description="延迟（毫秒）")  # 总耗时（毫秒）


# ============================================================================
# API 端点 1：联网搜索（非流式）
# ============================================================================

@router.post("/search", response_model=SearchResponse)  # 路由：POST /api/v1/search
async def web_search(request: SearchRequest):
    """
    联网搜索 + LLM 生成（非流式）

    工作流程：
    1. 调用博查 API 搜索
    2. 提取搜索结果
    3. 构建增强 Prompt
    4. 调用 LLM 生成答案
    5. 返回答案 + 来源
    
    功能说明：
      - 根据用户问题搜索互联网内容
      - 将搜索结果作为上下文提供给 LLM
      - LLM 基于搜索结果生成答案
      - 返回答案和引用来源
    
    参数：
      request (SearchRequest): 包含以下字段
        - query: 搜索关键词
        - model: LLM 模型名称
        - chat_history: 聊天历史（支持多轮对话）
        - max_results: 最大搜索结果数
        - max_tokens: 最大生成长度
        - temperature: 温度参数
    
    返回：
      SearchResponse: 包含以下字段
        - answer: LLM 生成的答案
        - sources: 搜索来源列表
        - search_results: 原始搜索结果
        - model: 使用的模型
        - tokens_used: 消耗的 token 数
        - latency_ms: 总耗时
    
    异常：
      HTTPException 404: 未找到搜索结果
      HTTPException 500: 搜索失败
    """
    start_time = time.time()  # 记录开始时间（用于计算延迟）

    try:
        # ========== 1. 执行搜索 ==========
        logger.info(f"🔍 开始搜索: {request.query}")

        # 调用博查 AI 搜索服务
        search_result = await bocha_client.search(
            query=request.query,  # 搜索关键词
            count=request.max_results  # 返回结果数量
        )

        # 提取搜索结果列表
        results = search_result.get("results", [])

        # 如果没有搜索结果，返回 404 错误
        if not results:
            raise HTTPException(
                status_code=404,
                detail="未找到相关搜索结果"
            )

        # ========== 2. 构建增强 Prompt ==========
        # 将搜索结果格式化为上下文字符串
        context = _build_search_context(results)

        # 构建系统提示词（包含搜索结果和回答要求）
        system_prompt = f"""你是一个智能助手，可以使用搜索结果来回答问题。
                        ## 当前时间
                        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

                        ## 搜索结果
                        {context}

                        ## 回答要求
                        1. 基于搜索结果回答问题
                        2. 引用来源时标注序号（如 [1]、[2]）
                        3. 使用 Markdown 格式
                        4. 结构清晰，分点列出
                        5. 如果搜索结果不足以回答问题，明确说明"""

        # 构建消息列表（用于 LLM 调用）
        messages = [{"role": "system", "content": system_prompt}]

        # 添加聊天历史（支持多轮对话）
        if request.chat_history:
            for msg in request.chat_history:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # 添加用户问题
        messages.append({
            "role": "user",
            "content": request.query
        })

        # ========== 3. 调用 LLM 生成答案 ==========
        logger.info(f" 调用 LLM: {request.model}")

        # 调用 OpenRouter API 生成答案
        response = await openai_client.chat.completions.create(
            model=request.model,  # 指定模型
            messages=messages,  # 消息列表（包含系统提示、历史、用户问题）
            max_tokens=request.max_tokens,  # 最大生成长度
            temperature=request.temperature  # 温度参数
        )

        # 提取生成的答案和 token 使用量
        answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        # ========== 4. 构建响应 ==========
        # 计算总耗时（毫秒）
        latency_ms = int((time.time() - start_time) * 1000)

        # 构建来源列表（提取关键信息）
        sources = [
            SearchSource(
                title=r["title"],
                url=r["url"],
                content=r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],  # 截断长内容
                publishedDate=r.get("publishedDate"),
                siteName=r.get("siteName")
            )
            for r in results
        ]

        logger.info(f" 搜索完成，耗时 {latency_ms}ms")

        # 返回标准响应
        return SearchResponse(
            answer=answer,  # LLM 生成的答案
            sources=sources,  # 搜索来源列表
            search_results=results,  # 原始搜索结果
            model=request.model,  # 使用的模型
            tokens_used=tokens_used,  # 消耗的 token 数
            latency_ms=latency_ms  # 总耗时
        )

    except HTTPException:
        raise  # 重新抛出 HTTP 异常
    except Exception as e:
        logger.error(f" 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


# ============================================================================
# API 端点 2：联网搜索（流式）
# ============================================================================

@router.post("/search/stream")  # 路由：POST /api/v1/search/stream
async def web_search_stream(request: SearchRequest):
    """
    联网搜索 + LLM 生成（流式）

    返回 Server-Sent Events 格式
    
    功能说明：
      - 实时返回搜索进度和生成内容
      - 适用于需要实时反馈的场景
    
    事件类型：
      - status: 状态更新（如 "正在搜索..."）
      - search_results: 搜索结果
      - content: LLM 生成的内容片段
      - error: 错误信息
      - [DONE]: 完成标记
    
    响应格式：
      data: {"type": "status", "message": "正在搜索..."}\n\n
      data: {"type": "search_results", "results": [...], "total": 10}\n\n
      data: {"type": "content", "content": "文本片段"}\n\n
      data: [DONE]\n\n
    """

    async def generate():
        """
        异步生成器函数
        
        逐步返回搜索和生成的内容
        """
        try:
            # ========== 1. 执行搜索 ==========
            logger.info(f"🔍 开始搜索: {request.query}")

            # 发送搜索状态（告知前端正在搜索）
            yield f"data: {json.dumps({'type': 'status', 'message': '正在搜索...'}, ensure_ascii=False)}\n\n"

            # 调用博查 AI 搜索
            search_result = await bocha_client.search(
                query=request.query,
                count=request.max_results
            )

            results = search_result.get("results", [])

            # 如果没有搜索结果，返回错误
            if not results:
                yield f"data: {json.dumps({'type': 'error', 'message': '未找到相关搜索结果'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"  # 发送完成标记
                return

            # 发送搜索结果（让前端显示来源）
            yield f"data: {json.dumps({'type': 'search_results', 'results': results, 'total': len(results)}, ensure_ascii=False)}\n\n"

            # ========== 2. 构建增强 Prompt ==========
            context = _build_search_context(results)

            system_prompt = f"""你是一个智能助手，可以使用搜索结果来回答问题。
                            ## 当前时间
                            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

                            ## 搜索结果
                            {context}

                            ## 回答要求
                            1. 基于搜索结果回答问题
                            2. 引用来源时标注序号（如 [1]、[2]）
                            3. 使用 Markdown 格式
                            4. 结构清晰，分点列出
                            5. 如果搜索结果不足以回答问题，明确说明"""

            # 构建消息列表
            messages = [{"role": "system", "content": system_prompt}]

            # 添加聊天历史
            if request.chat_history:
                for msg in request.chat_history:
                    messages.append({"role": msg.role, "content": msg.content})

            # 添加用户问题
            messages.append({"role": "user", "content": request.query})

            # ========== 3. 流式调用 LLM ==========
            logger.info(f" 调用 LLM: {request.model}")

            # 发送生成状态
            yield f"data: {json.dumps({'type': 'status', 'message': '正在生成回答...'}, ensure_ascii=False)}\n\n"

            # 调用 OpenRouter API（流式模式）
            stream = await openai_client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=True  # 启用流式传输
            )

            # ========== 4. 流式输出 ==========
            # 逐块返回 LLM 生成的内容
            async for chunk in stream:
                # 检查是否有内容（chunk 可能只包含元数据）
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # 发送内容片段
                    yield f"data: {json.dumps({'type': 'content', 'content': content}, ensure_ascii=False)}\n\n"

            # 发送完成标记
            yield "data: [DONE]\n\n"

            logger.info(" 流式搜索完成")

        except Exception as e:
            # 异常处理：发送错误信息
            logger.error(f" 流式搜索失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    # 返回流式响应
    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================================
# 内部函数
# ============================================================================

def _build_search_context(results: List[Dict[str, Any]]) -> str:
    """
    构建搜索上下文
    
    功能说明：
      - 将搜索结果格式化为结构化文本
      - 作为 LLM 的上下文信息
      - 包含标题、来源、内容等关键信息

    Args:
        results: 搜索结果列表（来自博查 AI）

    Returns:
        格式化的上下文字符串
        
    格式示例：
        [1] 文章标题
        来源: https://example.com
        网站: Example Site
        发布时间: 2024-01-01
        内容: 文章内容摘要...
    """
    context_parts = []  # 存储每个搜索结果的格式化文本

    # 遍历搜索结果，添加序号（从 1 开始）
    for i, result in enumerate(results, start=1):
        # 格式化单个搜索结果
        context_parts.append(f"""[{i}] {result['title']}
来源: {result['url']}
网站: {result.get('siteName', '未知')}
发布时间: {result.get('publishedDate', '未知')}
内容: {result['content']}
""")

    # 用换行符连接所有结果
    return "\n".join(context_parts)
