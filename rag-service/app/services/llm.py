"""
============================================================================
LLM（大语言模型）调用服务模块
============================================================================

文件位置：
  rag-service/app/services/llm.py

文件作用：
  负责调用大语言模型（LLM）生成回答，是 RAG 系统的"答案生成"环节

主要功能：
  1. LLM 调用 - 调用 OpenRouter API 生成回答
  2. 提示词构建 - 构建包含上下文的 RAG 提示词
  3. 错误处理 - 统一的错误处理和友好提示
  4. 参数控制 - 支持温度、最大 Token 等参数调整

技术栈：
  - httpx（异步 HTTP 客户端）
  - OpenRouter API（LLM API 提供商）
  - 支持多种模型（主模型 + 备用模型）

依赖文件：
  - app/core/config.py（配置管理）

API 要求：
  - OpenRouter API Key
  - 支持的 LLM 模型（如 GPT-4、Claude 等）

使用场景：
  1. RAG 问答 - 基于检索到的文档内容生成回答
  2. 文档摘要 - 生成文档摘要
  3. 内容分析 - 分析文档内容

使用示例：
    ```python
    from app.services.llm import get_llm_service
    
    service = get_llm_service()
    
    # 简单对话
    response = await service.chat([
        {"role": "user", "content": "什么是机器学习？"}
    ])
    # 返回: "机器学习是人工智能的一个分支..."
    
    # RAG 问答
    messages = service.build_rag_prompt(
        query="这个文档讲了什么？",
        context="文档内容...",
        pdf_name="机器学习入门.pdf"
    )
    response = await service.chat(messages)
    ```

RAG 流程：
  1. 用户提问 → 2. 向量检索 → 3. 构建提示词 → 4. LLM 生成 → 5. 返回答案
                                      ↑ 本模块负责

============================================================================
"""
import httpx  # HTTP 客户端，用于调用 API
from typing import List, Dict, Any, Optional
from loguru import logger  # 日志记录

from app.core.config import get_settings  # 获取配置

settings = get_settings()  # 全局配置实例


class LLMService:
    """
    LLM 服务类
    
    职责：
        - 调用 LLM API 生成回答
        - 构建 RAG 提示词（包含检索上下文）
        - 处理 API 错误和超时
        - 提供友好的错误提示
    
    属性：
        api_key: OpenRouter API 密钥
        base_url: API 基础 URL
        model_main: 主模型名称（如 gpt-4）
        model_fallback: 备用模型名称（主模型失败时使用）
    """

    def __init__(self):
        """
        初始化 LLM 服务
        
        工作流程：
            1. 加载配置（API Key、模型名称等）
            2. 记录初始化信息
        """
        # 从配置加载 API 密钥和模型信息
        self.api_key = settings.OPENROUTER_API_KEY  # API 密钥
        self.base_url = settings.OPENROUTER_BASE_URL  # API 基础 URL
        self.model_main = settings.LLM_MODEL_MAIN  # 主模型（如 gpt-4）
        self.model_fallback = settings.LLM_MODEL_FALLBACK  # 备用模型（如 gpt-3.5-turbo）

        # 记录初始化信息
        logger.info(f"LLM 服务初始化: model={self.model_main}")

    async def chat(
            self,
            messages: List[Dict[str, str]],
            model: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 2000,
    ) -> str:
        """
        调用 LLM 进行对话
        
        功能说明：
            调用 OpenRouter API 的 Chat Completions 接口生成回答
            支持多轮对话（通过 messages 列表）
        
        工作流程：
            1. 准备请求参数（模型、消息、温度等）
            2. 发送 HTTP POST 请求到 API
            3. 处理响应（提取生成的内容）
            4. 错误处理（网络错误、API 错误等）
            5. 返回生成的文本
        
        参数说明：
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
                     - role 可以是 "system"（系统提示）、"user"（用户）、"assistant"（AI）
                     - content 是消息内容
            
            model: 模型名称（可选）
                  - 不指定时使用主模型（self.model_main）
                  - 可选值：gpt-4, gpt-3.5-turbo, claude-3-opus 等
            
            temperature: 温度参数（0.0-2.0）
                        - 控制生成的随机性
                        - 0.0：确定性强，适合事实性回答
                        - 1.0：平衡创造性和准确性（默认）
                        - 2.0：高度随机，适合创意写作
            
            max_tokens: 最大生成 Token 数
                       - 控制回答长度
                       - 1 token ≈ 4 个英文字符 ≈ 1.5 个中文字符
                       - 2000 tokens ≈ 1500 个中文字
        
        Returns:
            生成的文本内容（字符串）
        
        Raises:
            ValueError: API 调用失败、响应为空、网络错误等
        
        示例：
            # 简单问答
            response = await chat([
                {"role": "user", "content": "什么是机器学习？"}
            ])
            # 返回: "机器学习是人工智能的一个分支..."
            
            # 多轮对话
            response = await chat([
                {"role": "system", "content": "你是一个专业的助手"},
                {"role": "user", "content": "什么是机器学习？"},
                {"role": "assistant", "content": "机器学习是..."},
                {"role": "user", "content": "能举个例子吗？"}
            ])
            
            # 调整参数
            response = await chat(
                messages=[{"role": "user", "content": "写一首诗"}],
                temperature=1.5,  # 提高创造性
                max_tokens=500    # 限制长度
            )
        """
        # 使用指定模型或默认主模型
        model = model or self.model_main

        # 记录调用信息（用于调试和监控）
        logger.info(f"调用 LLM: model={model}, messages={len(messages)}")

        try:
            # ========== 1. 发送 API 请求 ==========
            async with httpx.AsyncClient() as client:  # 创建异步 HTTP 客户端
                response = await client.post(
                    f"{self.base_url}/chat/completions",  # API 端点
                    headers={
                        "Authorization": f"Bearer {self.api_key}",  # API 密钥认证
                        "Content-Type": "application/json",  # JSON 格式
                        "HTTP-Referer": settings.APP_URL,  # 应用 URL（用于统计）
                        "X-Title": settings.APP_NAME,  # 应用名称（用于统计）
                    },
                    json={
                        # OpenAI Chat Completions API 标准参数
                        "model": model,  # 模型名称
                        "messages": messages,  # 消息列表
                        "temperature": temperature,  # 温度参数（控制随机性）
                        "max_tokens": max_tokens,  # 最大生成 Token 数
                        "top_p": 1,  # 核采样参数（1 表示不使用）
                        "frequency_penalty": 0,  # 频率惩罚（0 表示不惩罚重复）
                        "presence_penalty": 0,  # 存在惩罚（0 表示不惩罚已出现的词）
                    },
                    timeout=60.0,  # 超时时间 60 秒（生成较长内容可能需要更多时间）
                )

                # ========== 2. 错误处理 ==========
                # 检查 HTTP 状态码（2xx 表示成功，4xx/5xx 表示错误）
                if not response.is_success:
                    error_text = response.text  # 获取错误详情
                    logger.error(f"LLM API 错误: {response.status_code} - {error_text}")

                    # 根据错误码返回友好提示
                    if response.status_code == 401:
                        # 401 Unauthorized：API 密钥无效或过期
                        raise ValueError("AI 服务认证失败，请检查 API 密钥")
                    elif response.status_code == 429:
                        # 429 Too Many Requests：请求过于频繁（触发限流）
                        raise ValueError("AI 服务请求过于频繁，请稍后重试")
                    elif response.status_code == 500:
                        # 500 Internal Server Error：服务器内部错误
                        raise ValueError("AI 服务内部错误，请稍后重试")
                    else:
                        # 其他错误
                        raise ValueError(f"AI 服务暂时不可用 (状态码: {response.status_code})")

                # ========== 3. 解析响应 ==========
                data = response.json()  # 解析 JSON 响应

                # 验证响应格式
                # 标准格式：{"choices": [{"message": {"content": "..."}}]}
                if not data.get("choices") or len(data["choices"]) == 0:
                    logger.error(f"LLM 响应为空: {data}")
                    raise ValueError("AI 响应为空，请重试")

                # 提取生成的内容
                content = data["choices"][0]["message"]["content"]

                # 验证内容不为空
                if not content:
                    raise ValueError("AI 响应内容为空")

                # 记录成功信息
                logger.info(f"LLM 调用成功: 响应长度={len(content)}")

                return content

        # ========== 4. 异常处理 ==========
        except httpx.TimeoutException:
            # 超时异常（请求时间超过 60 秒）
            logger.error("LLM 调用超时")
            raise ValueError("AI 服务响应超时，请稍后重试")
        except httpx.RequestError as e:
            # 网络错误（如连接失败、DNS 解析失败）
            logger.error(f"LLM 网络错误: {e}")
            raise ValueError(f"网络错误: {str(e)}")
        except Exception as e:
            # 其他未知错误
            logger.error(f"LLM 调用失败: {e}")
            raise ValueError(f"AI 服务调用失败: {str(e)}")

    def build_rag_prompt(
            self,
            query: str,
            context: str,
            pdf_name: str,
            total_pages: Optional[int] = None,
            total_chunks: int = 0,
            chunks_retrieved: int = 0,
    ) -> List[Dict[str, str]]:
        """
        构建 RAG（检索增强生成）提示词
        
        功能说明：
            将用户问题、检索到的文档内容、文档信息组合成完整的提示词
            这是 RAG 系统的核心：让 LLM 基于检索到的内容生成回答
        
        RAG 原理：
            传统 LLM：用户问题 → LLM → 回答（可能不准确或过时）
            RAG 系统：用户问题 → 检索相关文档 → LLM（基于文档）→ 准确回答
                                              ↑ 本函数构建的提示词
        
        提示词结构：
            1. System Prompt（系统提示）
               - 定义 AI 的角色（PDF 文档分析助手）
               - 提供检索到的上下文内容
               - 明确回答要求（基于文档、引用来源、准确性等）
               - 提供文档信息（文件名、页数等）
            
            2. User Prompt（用户提示）
               - 用户的原始问题
        
        工作流程：
            1. 构建系统提示（包含上下文和回答要求）
            2. 构建用户提示（用户问题）
            3. 返回消息列表（供 chat() 方法使用）
        
        Args:
            query: 用户问题（必填）
                  例如："这个文档讲了什么？"
            
            context: 检索到的上下文内容（必填）
                    格式：多个文档块的拼接
                    例如："来源1（第3页）：机器学习是...\n来源2（第5页）：深度学习是..."
            
            pdf_name: PDF 文件名（必填）
                     例如："机器学习入门.pdf"
            
            total_pages: 总页数（可选）
                        例如：50
            
            total_chunks: 文档总块数（可选）
                         例如：120（整个文档被切分成 120 块）
            
            chunks_retrieved: 检索到的块数（可选）
                             例如：5（从 120 块中检索到 5 块相关内容）
        
        Returns:
            消息列表，格式：[
                {"role": "system", "content": "系统提示..."},
                {"role": "user", "content": "用户问题..."}
            ]
        
        示例：
            # 构建 RAG 提示词
            messages = build_rag_prompt(
                query="这个文档讲了什么？",
                context="来源1（第3页）：本文介绍机器学习的基本概念...",
                pdf_name="机器学习入门.pdf",
                total_pages=50,
                total_chunks=120,
                chunks_retrieved=5
            )
            
            # 调用 LLM 生成回答
            response = await chat(messages)
            # 返回: "根据文档内容，这是一份介绍机器学习基本概念的教程..."
        """
        # ========== 1. 构建系统提示 ==========
        # 系统提示定义了 AI 的角色、任务和约束
        system_prompt = f"""你是一个专业的 PDF 文档分析助手。用户上传了一个名为 "{pdf_name}" 的 PDF 文件。

                            ## 📚 相关文档内容（基于语义检索）：
                            {context}

                            ## 📋 回答要求：
                            1. **基于检索内容**：优先使用上述检索到的相关内容回答问题
                            2. **引用来源**：回答时可以标注来源编号，如"根据来源1..."或"第X页提到..."
                            3. **准确性**：如果检索内容不足以完整回答问题，明确告知用户
                            4. **格式美化**：使用 Markdown 格式，提高可读性
                            5. **友好语气**：保持专业、准确、友好的语气
                            6. **中文回答**：使用简体中文回答

                            ## 📊 文档信息：
                            - 文件名：{pdf_name}
                            - 总页数：{total_pages or 'N/A'}
                            - 文档块数：{total_chunks}
                            - 检索到的相关块：{chunks_retrieved}

                            ## ⚠️ 注意事项：
                            - 不要编造文档中不存在的内容
                            - 如果问题超出检索内容范围，诚实告知用户
                            - 可以建议用户换一种方式提问"""

        # ========== 2. 构建用户提示 ==========
        # 用户提示就是用户的原始问题
        user_prompt = f"用户问题：{query}"

        # ========== 3. 返回消息列表 ==========
        # 返回标准的 Chat Completions 格式
        return [
            {"role": "system", "content": system_prompt},  # 系统提示（定义角色和任务）
            {"role": "user", "content": user_prompt},  # 用户提示（用户问题）
        ]


# ============================================================================
# 全局服务实例（单例模式）
# ============================================================================

_llm_service: Optional[LLMService] = None  # 全局服务实例（初始为 None）


def get_llm_service() -> LLMService:
    """
    获取 LLM 服务实例（单例模式）
    
    单例模式说明：
        - 全局只创建一个 LLMService 实例
        - 避免重复初始化（节省资源）
        - 所有地方共享同一个配置
    
    工作流程：
        1. 检查全局实例是否已创建
        2. 如果未创建，创建新实例
        3. 返回实例
    
    Returns:
        LLMService 实例
    
    示例：
        service = get_llm_service()
        response = await service.chat([
            {"role": "user", "content": "你好"}
        ])
    """
    global _llm_service  # 声明使用全局变量

    # 如果实例未创建，创建新实例
    if _llm_service is None:
        _llm_service = LLMService()

    return _llm_service
