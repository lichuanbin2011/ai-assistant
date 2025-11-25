"""
============================================================================
LLM 服务 - 仅支持 OpenRouter
OpenRouter 提供统一接口访问多个 LLM 提供商，无地区限制
============================================================================

文件位置：
  llm-service/app/services/llm_service.py

文件作用：
  封装 LLM 调用逻辑，提供统一的生成接口

主要功能：
  1. 流式生成 - 支持 SSE 流式输出
  2. 非流式生成 - 一次性返回完整结果
  3. 多模型支持 - 通过 OpenRouter 访问多个模型
  4. 消息构造 - 自动添加系统提示词
  5. 健康检查 - 验证服务可用性

支持的模型：
  - OpenAI: GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo
  - Anthropic: Claude 3.5 Sonnet, Claude 3 Opus/Sonnet/Haiku
  - Google: Gemini Pro 1.5, Gemini Pro
  - Meta: Llama 3.1 70B/8B
  - Mistral: Mistral Large/Medium
  - 其他: Perplexity Sonar 等

技术栈：
  - OpenAI SDK（兼容 OpenRouter）
  - AsyncIO（异步编程）
  - SSE（Server-Sent Events）

使用场景：
  - 对话生成（/api/v1/generate）
  - 流式生成（/api/v1/generate/stream）
  - 模型列表（/api/v1/models）

依赖文件：
  - app/core/config.py（配置管理）
  - app/core/logger.py（日志记录）
  - app/api/v1/generate.py（生成接口）

============================================================================
"""
from typing import List, Dict, Optional, AsyncGenerator  # 类型注解
from openai import AsyncOpenAI  # OpenAI 异步客户端（兼容 OpenRouter）
import json  # JSON 序列化
import traceback  # 异常堆栈追踪
from app.core.config import settings  # 应用配置
from app.core.logger import logger  # 日志记录器


# ============================================================================
# LLM 服务类
# ============================================================================

class LLMService:
    """
    LLM 服务 - OpenRouter 版本
    
    功能说明：
      - 封装 OpenRouter API 调用
      - 提供流式和非流式生成接口
      - 自动处理消息格式化
      - 支持多种 LLM 模型
    
    使用示例：
        service = LLMService()
        
        # 流式生成
        async for chunk in service.generate(messages, stream=True):
            print(chunk)
        
        # 非流式生成
        result = await service.generate(messages, stream=False)
        print(result["response"])
    """

    def __init__(self):
        """
        初始化服务
        
        功能说明：
          - 从配置读取默认参数
          - 初始化 OpenRouter 客户端
          - 验证 API Key 配置
        
        Raises:
            ValueError: API Key 未配置时抛出异常
        """
        # ========== 1. 读取默认配置 ==========
        self.default_temperature = settings.DEFAULT_TEMPERATURE  # 默认温度（0.7）
        self.default_max_tokens = settings.DEFAULT_MAX_TOKENS  # 默认最大 token 数（2000）

        # ========== 2. 验证 API Key ==========
        # 初始化 OpenRouter 客户端
        if not settings.OPENROUTER_API_KEY:
            logger.error(" OpenRouter API Key 未配置")
            raise ValueError("OPENROUTER_API_KEY 未在环境变量中配置")

        # ========== 3. 初始化 OpenRouter 客户端 ==========
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,  # API 密钥
            base_url=settings.OPENROUTER_BASE_URL,  # API 地址（https://openrouter.ai/api/v1）
            default_headers={
                "HTTP-Referer": "http://localhost:8002",  # 请求来源（OpenRouter 要求）
                "X-Title": "LLM Service"  # 应用标题（OpenRouter 要求）
            },
            timeout=settings.REQUEST_TIMEOUT  # 请求超时时间（60 秒）
        )

        # ========== 4. 输出初始化日志 ==========
        logger.info("=" * 60)
        logger.info("初始化 LLMService (OpenRouter)")
        logger.info(f"OpenRouter 客户端已初始化")
        logger.info(f"Base URL: {settings.OPENROUTER_BASE_URL}")
        logger.info(f"默认模型: {settings.OPENROUTER_DEFAULT_MODEL}")
        logger.info(f"默认温度: {self.default_temperature}")
        logger.info(f"默认最大 Token: {self.default_max_tokens}")
        logger.info("=" * 60)

    def _build_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        构造消息列表
        
        功能说明：
          - 检查是否有系统消息
          - 如果没有，自动添加默认系统提示词
          - 格式化所有消息
        
        Args:
            messages: 原始消息列表
                格式：[{"role": "user", "content": "你好"}]
        
        Returns:
            格式化后的消息列表
                格式：[
                    {"role": "system", "content": "系统提示词"},
                    {"role": "user", "content": "你好"}
                ]
        
        Raises:
            Exception: 消息构造失败时抛出异常
        """
        try:
            formatted_messages = []

            # ========== 1. 检查是否已有系统消息 ==========
            # 遍历消息列表，查找 role 为 "system" 的消息
            has_system = any(msg.get("role") == "system" for msg in messages)

            # ========== 2. 如果没有系统消息，添加默认系统提示词 ==========
            if not has_system:
                system_prompt = """你是一个专业、友好的 AI 助手。

回答原则：
1. 结构清晰，使用 Markdown 格式
2. 详细全面，提供完整信息
3. 实用可行，给出具体建议
4. 友好亲和，适当使用表情符号

请根据用户的问题，提供准确、有帮助的回答。"""

                formatted_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
                logger.debug("添加了默认系统提示词")

            # ========== 3. 添加所有用户消息 ==========
            for msg in messages:
                formatted_messages.append({
                    "role": msg["role"],  # 角色（user/assistant/system）
                    "content": msg["content"]  # 内容（字符串或多模态数组）
                })

            logger.debug(f"构造消息完成，总消息数: {len(formatted_messages)}")
            return formatted_messages

        except Exception as e:
            logger.error(f"构造消息失败: {e}")
            logger.error(traceback.format_exc())  # 输出完整堆栈
            raise

    async def generate(
        self,
        messages: List[Dict],  # 对话消息列表（必填）
        model: Optional[str] = None,  # 模型名称（可选，默认使用配置值）
        temperature: Optional[float] = None,  # 温度参数（可选，默认使用配置值）
        max_tokens: Optional[int] = None,  # 最大 token 数（可选，默认使用配置值）
        stream: bool = True,  # 是否流式返回（默认 True）
        **kwargs  # 其他参数（预留扩展）
    ):
        """
        生成响应（统一接口）
        
        功能说明：
          - 统一的生成接口，根据 stream 参数选择生成方式
          - 自动使用默认配置（如果参数未指定）
          - 自动构造消息格式
        
        Args:
            messages: 对话消息列表（必填）
                格式：[{"role": "user", "content": "你好"}]
            
            model: 模型名称（可选，默认使用配置值）
                格式：OpenRouter 格式，如 "openai/gpt-4o-mini"
                示例："openai/gpt-4o", "anthropic/claude-3.5-sonnet"
            
            temperature: 温度参数（可选，默认使用配置值）
                范围：0-2
                说明：
                  - 0: 确定性输出（适合事实性问答）
                  - 0.7: 平衡（默认值）
                  - 2: 高随机性（适合创意写作）
            
            max_tokens: 最大生成 token 数（可选，默认使用配置值）
                范围：1-模型上下文长度
                说明：限制生成的最大长度
            
            stream: 是否流式返回（默认 True）
                - True: 流式返回（SSE 格式）
                - False: 一次性返回完整结果
            
            **kwargs: 其他参数（预留扩展）

        Returns:
            流式: AsyncGenerator[str, None]（SSE 格式的数据流）
            非流式: Dict[str, Any]（包含响应内容和元数据）
        
        Raises:
            Exception: 生成失败时抛出异常
        
        使用示例：
            # 流式生成
            async for chunk in service.generate(messages, stream=True):
                print(chunk)
            
            # 非流式生成
            result = await service.generate(messages, stream=False)
            print(result["response"])
        """
        try:
            # ========== 1. 参数处理（使用默认值） ==========
            used_model = model or settings.OPENROUTER_DEFAULT_MODEL  # 使用指定模型或默认模型
            used_temp = temperature if temperature is not None else self.default_temperature  # 使用指定温度或默认温度
            used_max_tokens = max_tokens or self.default_max_tokens  # 使用指定最大 token 数或默认值

            # ========== 2. 输出生成日志 ==========
            logger.info("=" * 60)
            logger.info("开始生成响应")
            logger.info(f"模型: {used_model}")
            logger.info(f"温度: {used_temp}")
            logger.info(f"最大 Token: {used_max_tokens}")
            logger.info(f"流式: {stream}")
            logger.info(f"消息数: {len(messages)}")
            logger.info("=" * 60)

            # ========== 3. 构造消息 ==========
            formatted_messages = self._build_messages(messages)

            # ========== 4. 根据 stream 参数选择生成方式 ==========
            if stream:
                # 流式生成（返回 AsyncGenerator）
                return self._stream_generate(
                    formatted_messages,
                    used_model,
                    used_temp,
                    used_max_tokens
                )
            else:
                # 非流式生成（返回 Dict）
                return await self._normal_generate(
                    formatted_messages,
                    used_model,
                    used_temp,
                    used_max_tokens
                )

        except Exception as e:
            logger.error(f"生成失败: {e}")
            logger.error(traceback.format_exc())  # 输出完整堆栈
            raise

    async def _normal_generate(
        self,
        messages: List[Dict],  # 格式化后的消息列表
        model: str,  # 模型名称
        temperature: float,  # 温度参数
        max_tokens: int  # 最大 token 数
    ) -> Dict:
        """
        非流式生成
        
        功能说明：
          - 一次性返回完整结果
          - 包含响应内容和 token 使用统计
        
        Args:
            messages: 格式化后的消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            包含响应内容和元数据的字典：
            {
                "response": "AI 生成的回复内容",
                "model": "openai/gpt-4o-mini",
                "provider": "openrouter",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        
        Raises:
            Exception: 生成失败时抛出异常
        """
        try:
            logger.info("发送非流式请求...")

            # ========== 1. 调用 OpenRouter API ==========
            response = await self.client.chat.completions.create(
                model=model,  # 模型名称
                messages=messages,  # 消息列表
                temperature=temperature,  # 温度参数
                max_tokens=max_tokens,  # 最大 token 数
                stream=False  # 非流式
            )

            # ========== 2. 提取响应内容 ==========
            content = response.choices[0].message.content  # AI 生成的回复内容
            usage = response.usage  # token 使用统计

            # ========== 3. 输出成功日志 ==========
            logger.info(" 非流式生成成功")
            logger.info(f" 响应长度: {len(content)} 字符")
            logger.info(f"Token 使用: {usage.total_tokens} (输入: {usage.prompt_tokens}, 输出: {usage.completion_tokens})")

            # ========== 4. 返回结果 ==========
            return {
                "response": content,  # AI 生成的回复内容
                "model": model,  # 使用的模型
                "provider": "openrouter",  # 提供商
                "usage": {  # token 使用统计
                    "prompt_tokens": usage.prompt_tokens,  # 输入 token 数
                    "completion_tokens": usage.completion_tokens,  # 输出 token 数
                    "total_tokens": usage.total_tokens  # 总 token 数
                }
            }

        except Exception as e:
            logger.error(f" 非流式生成失败: {e}")
            logger.error(traceback.format_exc())  # 输出完整堆栈
            raise

    async def _stream_generate(
        self,
        messages: List[Dict],  # 格式化后的消息列表
        model: str,  # 模型名称
        temperature: float,  # 温度参数
        max_tokens: int  # 最大 token 数
    ) -> AsyncGenerator[str, None]:
        """
        流式生成（SSE 格式）
        
        功能说明：
          - 实时返回生成的内容片段
          - 使用 SSE（Server-Sent Events）格式
          - 自动发送完成信号和错误信号
        
        Args:
            messages: 格式化后的消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数

        Yields:
            SSE 格式的数据流：
            
            # 内容块
            data: {"type": "content", "content": "文本片段", "provider": "openrouter", "model": "..."}\n\n
            
            # 完成信号
            data: {"type": "done", "provider": "openrouter", "model": "...", "stats": {...}}\n\n
            
            # 错误信号
            data: {"type": "error", "error": "错误信息", "provider": "openrouter", "model": "..."}\n\n
        
        使用示例：
            async for chunk in service._stream_generate(...):
                print(chunk)
        """
        try:
            logger.info("发送流式请求...")

            # ========== 1. 调用 OpenRouter API（流式） ==========
            stream = await self.client.chat.completions.create(
                model=model,  # 模型名称
                messages=messages,  # 消息列表
                temperature=temperature,  # 温度参数
                max_tokens=max_tokens,  # 最大 token 数
                stream=True  # 流式
            )

            # ========== 2. 初始化统计变量 ==========
            chunk_count = 0  # 块计数
            total_content = ""  # 总内容

            # ========== 3. 处理流式响应 ==========
            async for chunk in stream:
                # 检查是否有内容
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta  # 增量内容

                    # 处理内容块
                    if delta.content:
                        chunk_count += 1  # 块计数 +1
                        total_content += delta.content  # 累加内容

                        # 构造 SSE 数据
                        data = {
                            "type": "content",  # 类型：内容块
                            "content": delta.content,  # 内容片段
                            "provider": "openrouter",  # 提供商
                            "model": model  # 模型名称
                        }
                        # 输出 SSE 格式：data: {...}\n\n
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            # ========== 4. 发送完成信号 ==========
            done_data = {
                "type": "done",  # 类型：完成
                "provider": "openrouter",  # 提供商
                "model": model,  # 模型名称
                "stats": {  # 统计信息
                    "chunks": chunk_count,  # 总块数
                    "total_length": len(total_content)  # 总字符数
                }
            }
            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"

            # ========== 5. 输出成功日志 ==========
            logger.info(" 流式生成完成")
            logger.info(f"总块数: {chunk_count}")
            logger.info(f" 总字符数: {len(total_content)}")

        except Exception as e:
            logger.error(f" 流式生成失败: {e}")
            logger.error(traceback.format_exc())  # 输出完整堆栈

            # ========== 6. 发送错误信号 ==========
            error_data = {
                "type": "error",  # 类型：错误
                "error": str(e),  # 错误信息
                "provider": "openrouter",  # 提供商
                "model": model  # 模型名称
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    async def list_models(self) -> List[str]:
        """
        获取可用模型列表（OpenRouter 支持的模型）
        
        功能说明：
          - 返回 OpenRouter 常用模型列表
          - 包含 OpenAI、Anthropic、Google、Meta 等多个提供商
        
        Returns:
            模型名称列表（OpenRouter 格式）
            
        使用示例：
            models = await service.list_models()
            print(models)  # ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", ...]
        """
        # OpenRouter 常用模型列表
        models = [
            # ========== OpenAI 模型 ==========
            "openai/gpt-4o",  # GPT-4o（最新优化版本）
            "openai/gpt-4o-mini",  # GPT-4o Mini（轻量版本）
            "openai/gpt-4-turbo",  # GPT-4 Turbo（高性能版本）
            "openai/gpt-3.5-turbo",  # GPT-3.5 Turbo（经典版本）

            # ========== Anthropic 模型 ==========
            "anthropic/claude-3.5-sonnet",  # Claude 3.5 Sonnet（最新版本）
            "anthropic/claude-3-opus",  # Claude 3 Opus（最强版本）
            "anthropic/claude-3-sonnet",  # Claude 3 Sonnet（平衡版本）
            "anthropic/claude-3-haiku",  # Claude 3 Haiku（快速版本）

            # ========== Google 模型 ==========
            "google/gemini-pro-1.5",  # Gemini Pro 1.5（最新版本）
            "google/gemini-pro",  # Gemini Pro（标准版本）

            # ========== Meta 模型 ==========
            "meta-llama/llama-3.1-70b-instruct",  # Llama 3.1 70B（大模型）
            "meta-llama/llama-3.1-8b-instruct",  # Llama 3.1 8B（小模型）

            # ========== Mistral 模型 ==========
            "mistralai/mistral-large",  # Mistral Large（大模型）
            "mistralai/mistral-medium",  # Mistral Medium（中等模型）

            # ========== 其他模型 ==========
            "perplexity/llama-3.1-sonar-large-128k-online",  # Perplexity Sonar（联网搜索）
        ]

        logger.info(f"可用模型数: {len(models)}")
        return models

    def get_model_info(self, model: str) -> Dict:
        """
        获取模型信息
        
        功能说明：
          - 返回模型的详细信息
          - 包含名称、提供商、上下文长度、描述等
        
        Args:
            model: 模型名称（OpenRouter 格式）
                示例："openai/gpt-4o"

        Returns:
            模型信息字典：
            {
                "name": "GPT-4o",
                "provider": "OpenAI",
                "context_length": 128000,
                "description": "最新的 GPT-4 优化版本"
            }
        
        使用示例:
            info = service.get_model_info("openai/gpt-4o")
            print(info["name"])  # "GPT-4o"
        """
        # 简单的模型信息映射
        model_info = {
            "openai/gpt-4o": {
                "name": "GPT-4o",
                "provider": "OpenAI",
                "context_length": 128000,
                "description": "最新的 GPT-4 优化版本"
            },
            "openai/gpt-4o-mini": {
                "name": "GPT-4o Mini",
                "provider": "OpenAI",
                "context_length": 128000,
                "description": "GPT-4o 的轻量版本，速度更快"
            },
            "anthropic/claude-3.5-sonnet": {
                "name": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "context_length": 200000,
                "description": "Claude 3.5 系列的平衡版本"
            },
            "google/gemini-pro-1.5": {
                "name": "Gemini Pro 1.5",
                "provider": "Google",
                "context_length": 1000000,
                "description": "Google 的多模态大模型"
            }
        }

        # 返回模型信息，如果未找到则返回默认信息
        return model_info.get(model, {
            "name": model,
            "provider": "Unknown",
            "context_length": 0,
            "description": "模型信息未知"
        })

    async def health_check(self) -> Dict:
        """
        健康检查
        
        功能说明：
          - 验证 OpenRouter 连接是否正常
          - 发送一个简单的测试请求
        
        Returns:
            健康状态字典：
            {
                "status": "healthy",
                "provider": "openrouter",
                "model": "openai/gpt-4o-mini",
                "message": "OpenRouter 连接正常"
            }
        
        使用示例：
            health = await service.health_check()
            print(health["status"])  # "healthy" 或 "unhealthy"
        """
        try:
            # ========== 1. 构造测试消息 ==========
            # 尝试发送一个简单的请求来验证连接
            test_messages = [
                {"role": "user", "content": "hi"}
            ]

            # ========== 2. 发送测试请求 ==========
            response = await self.client.chat.completions.create(
                model=settings.OPENROUTER_DEFAULT_MODEL,  # 使用默认模型
                messages=test_messages,  # 测试消息
                max_tokens=10,  # 限制生成长度（节省成本）
                stream=False  # 非流式
            )

            # ========== 3. 返回健康状态 ==========
            return {
                "status": "healthy",  # 状态：健康
                "provider": "openrouter",  # 提供商
                "model": settings.OPENROUTER_DEFAULT_MODEL,  # 使用的模型
                "message": "OpenRouter 连接正常"  # 消息
            }

        except Exception as e:
            # ========== 4. 返回异常状态 ==========
            logger.error(f"健康检查失败: {e}")
            return {
                "status": "unhealthy",  # 状态：不健康
                "provider": "openrouter",  # 提供商
                "error": str(e),  # 错误信息
                "message": "OpenRouter 连接失败"  # 消息
            }

    def __del__(self):
        """
        清理资源
        
        功能说明：
          - 在对象销毁时自动调用
          - 清理客户端连接等资源
        """
        logger.info(" LLMService 正在清理资源...")


# ============================================================================
# 使用示例
# ============================================================================
# from app.services.llm_service import LLMService
#
# # 初始化服务
# service = LLMService()
#
# # 流式生成
# messages = [{"role": "user", "content": "你好"}]
# async for chunk in service.generate(messages, stream=True):
#     print(chunk)
#
# # 非流式生成
# result = await service.generate(messages, stream=False)
# print(result["response"])
#
# # 获取模型列表
# models = await service.list_models()
# print(models)
#
# # 健康检查
# health = await service.health_check()
# print(health["status"])

# ============================================================================
# SSE 格式说明
# ============================================================================
# Server-Sent Events (SSE) 格式：
#   data: {"type": "content", "content": "文本片段"}\n\n
#   data: {"type": "done", "stats": {...}}\n\n
#   data: [DONE]\n\n
#
# 前端接收示例（JavaScript）：
#   const eventSource = new EventSource('/api/v1/generate/stream');
#   eventSource.onmessage = (event) => {
#       const data = JSON.parse(event.data);
#       if (data.type === 'content') {
#           console.log(data.content);
#       } else if (data.type === 'done') {
#           eventSource.close();
#       }
#   };
