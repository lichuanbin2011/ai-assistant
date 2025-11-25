"""
============================================================================
查询重写模块
============================================================================

文件位置：
  rag-service/app/core/rag/query_rewrite.py

文件作用：
  提供查询重写（Query Rewriting）功能，优化用户查询以提高检索效果

主要功能：
  1. 查询标准化 - 去除口语化，转换为书面表达
  2. 查询分解 - 将复合问题拆解为多个子问题
  3. 查询扩展 - 添加同义词和相关表达
  4. LLM 调用 - 使用大语言模型进行查询重写

查询重写流程：
  原始查询 → 标准化 → 判断类型 → 分解/扩展 → 返回重写结果

使用场景：
  - 口语化查询：去除语气词，转换为书面表达
  - 复合查询：拆解为多个子问题，分别检索
  - 简单查询：添加同义词，提高召回率

技术栈：
  - httpx（异步 HTTP 客户端）
  - OpenRouter API（LLM 服务）

依赖文件：
  - app/core/config.py（配置管理）

============================================================================
"""
import httpx  # 异步 HTTP 客户端
from typing import Dict, Any  # 类型注解
from loguru import logger  # 日志记录器

from app.core.config import get_settings  # 配置管理

settings = get_settings()  # 获取配置


# ============================================================================
# 查询重写器类
# ============================================================================

class QueryRewriter:
    """
    查询重写器
    
    功能说明：
      - 优化用户查询，提高检索效果
      - 支持查询标准化、分解、扩展
      - 使用 LLM 进行智能重写
    
    重写策略：
      1. 标准化：去除口语化，转换为书面表达
      2. 分解：将复合问题拆解为多个子问题
      3. 扩展：添加同义词和相关表达
    
    使用示例：
        ```python
        rewriter = QueryRewriter()
        result = await rewriter.rewrite("这个文档讲了啥呀？")
        # 返回：
        # {
        #   "original_query": "这个文档讲了啥呀？",
        #   "final_query": "文档主要内容",
        #   "query_type": "expansion",
        #   "steps": ["标准化完成", "使用查询扩展"]
        # }
        ```
    """

    def __init__(self):
        """
        初始化查询重写器
        
        功能说明：
          - 读取配置（是否启用、使用的模型）
          - 记录初始化日志
        
        配置项：
          - ENABLE_QUERY_REWRITE: 是否启用查询重写
          - LLM_MODEL_REWRITE: 使用的 LLM 模型
        """
        self.enabled = settings.ENABLE_QUERY_REWRITE  # 是否启用查询重写
        self.model = settings.LLM_MODEL_REWRITE  # 使用的 LLM 模型
        logger.info(f"查询重写器初始化: enabled={self.enabled}, model={self.model}")

    async def rewrite(self, query: str) -> Dict[str, Any]:
        """
        重写查询
        
        功能说明：
          - 对用户查询进行智能重写
          - 根据查询类型选择不同的重写策略
          - 返回重写结果和中间步骤
        
        重写流程：
          1. 查询标准化（去除口语化）
          2. 判断查询类型（复合问题 vs 简单问题）
          3. 复合问题 → 查询分解
          4. 简单问题 → 查询扩展
          5. 返回重写结果
        
        Args:
            query: 原始查询
                - 类型：字符串
                - 示例："这个文档讲了啥呀？"

        Returns:
            重写结果：
            {
                "original_query": "这个文档讲了啥呀？",
                "normalized_query": "文档主要内容",
                "final_query": "文档主要内容 核心观点 关键信息",
                "query_type": "expansion",
                "steps": ["标准化完成", "使用查询扩展"],
                "sub_queries": null  # 仅分解时有值
            }
        
        查询类型：
          - original: 未重写（查询重写已禁用）
          - expansion: 查询扩展（简单问题）
          - decomposition: 查询分解（复合问题）
          - fallback: 重写失败（使用原始查询）
        
        复合问题关键词：
          - "和"、"与"、"或者"、"以及"
          - "区别"、"对比"、"比较"
        
        使用示例：
            ```python
            rewriter = QueryRewriter()
            
            # 简单问题
            result = await rewriter.rewrite("什么是机器学习？")
            # query_type: "expansion"
            # final_query: "机器学习 定义 概念 含义"
            
            # 复合问题
            result = await rewriter.rewrite("机器学习和深度学习的区别？")
            # query_type: "decomposition"
            # sub_queries: "1. 什么是机器学习\n2. 什么是深度学习\n3. 两者的区别"
            ```
        """
        # ========== 初始化结果 ==========
        result = {
            "original_query": query,  # 原始查询
            "final_query": query,  # 最终查询（初始为原始查询）
            "query_type": "original",  # 查询类型（初始为 original）
            "steps": [],  # 重写步骤
        }

        # ========== 检查是否启用 ==========
        if not self.enabled:
            logger.debug("查询重写已禁用")
            return result

        try:
            # ================================================================
            # 步骤1：查询标准化
            # ================================================================
            # 功能说明：
            #   - 去除口语化内容（如"emmm"、"呀"、"吧"等语气词）
            #   - 去除冗余表达（如"能不能"、"可以吗"等）
            #   - 转换为书面化、正式的表达
            normalized = await self._normalize_query(query)
            if normalized:
                result["normalized_query"] = normalized  # 标准化后的查询
                result["final_query"] = normalized  # 更新最终查询
                result["steps"].append("标准化完成")
            else:
                result["steps"].append("标准化失败")
            # 示例：
            #   原始："这个文档讲了啥呀？"
            #   标准化："文档主要内容"

            # ================================================================
            # 步骤2：判断问题类型
            # ================================================================
            # 功能说明：
            #   - 判断是复合问题还是简单问题
            #   - 复合问题：包含"和"、"区别"、"对比"等关键词
            #   - 简单问题：不包含上述关键词
            query_for_analysis = result["final_query"]  # 使用标准化后的查询
            is_compound = any(kw in query_for_analysis for kw in ["和", "与", "或者", "以及", "区别", "对比", "比较"])
            # 说明：
            #   - any(): 判断是否包含任意一个关键词
            #   - 关键词列表：["和", "与", "或者", "以及", "区别", "对比", "比较"]

            if is_compound:
                # ============================================================
                # 复合问题 → 查询分解
                # ============================================================
                # 功能说明：
                #   - 将复合问题拆解为 2-3 个独立的子问题
                #   - 每个子问题应该独立且完整
                #   - 子问题应该覆盖原问题的所有方面
                result["query_type"] = "decomposition"
                result["steps"].append("使用查询分解")

                decomposed = await self._decompose_query(query_for_analysis)
                if decomposed:
                    result["sub_queries"] = decomposed  # 子问题列表
                    # 合并子问题（去除序号）
                    result["final_query"] = " ".join(decomposed.split("\n")).replace("1.", "").replace("2.",
                                                                                                       "").replace("3.",
                                                                                                                   "")
                else:
                    result["steps"].append("查询分解失败")
                # 示例：
                #   原始："机器学习和深度学习的区别？"
                #   分解："1. 什么是机器学习\n2. 什么是深度学习\n3. 两者的区别"
                #   合并："什么是机器学习 什么是深度学习 两者的区别"
            else:
                # ============================================================
                # 标准问题 → 查询扩展
                # ============================================================
                # 功能说明：
                #   - 添加同义词和相关表达
                #   - 提高检索召回率
                #   - 保持问题的核心意图不变
                result["query_type"] = "expansion"
                result["steps"].append("使用查询扩展")

                expanded = await self._expand_query(query_for_analysis)
                if expanded:
                    result["final_query"] = expanded  # 扩展后的查询
                else:
                    result["steps"].append("查询扩展失败")
                # 示例：
                #   原始："什么是机器学习？"
                #   扩展："机器学习 定义 概念 含义 人工智能"

            logger.info(f"查询重写完成: {result['query_type']}")

        except Exception as e:
            # ========== 异常处理 ==========
            logger.error(f"查询重写失败: {e}")
            result["query_type"] = "fallback"  # 标记为失败
            result["error"] = str(e)  # 错误信息
            result["steps"].append("查询重写失败")

        return result

    async def _normalize_query(self, query: str) -> str:
        """
        标准化查询
        
        功能说明：
          - 去除口语化内容（语气词、冗余表达）
          - 转换为书面化、正式的表达
          - 保持问题的核心意图不变
        
        Args:
            query: 原始查询
        
        Returns:
            标准化后的查询
        
        示例：
            原始："这个文档讲了啥呀？"
            标准化："文档主要内容"
            
            原始："能不能告诉我机器学习是什么？"
            标准化："机器学习定义"
        """
        # ========== 构建 Prompt ==========
        prompt = f"""请将以下用户问题改写成更适合文档检索的标准化表达。

                    要求：
                    1. 去除口语化内容（如"emmm"、"呀"、"吧"等语气词）
                    2. 去除冗余表达（如"能不能"、"可以吗"等）
                    3. 使用书面化、正式的表达
                    4. 保持问题的核心意图不变
                    5. 只返回改写后的问题，不要任何解释

                    原始问题：{query}

                    改写后的问题："""
        # 说明：
        #   - 使用 LLM 进行标准化
        #   - max_tokens=200: 限制输出长度

        return await self._call_llm(prompt, max_tokens=200)

    async def _decompose_query(self, query: str) -> str:
        """
        分解查询
        
        功能说明：
          - 将复合问题拆解为 2-3 个独立的子问题
          - 每个子问题应该独立且完整
          - 子问题应该覆盖原问题的所有方面
        
        Args:
            query: 原始查询
        
        Returns:
            子问题列表（换行分隔）
        
        示例：
            原始："机器学习和深度学习的区别？"
            分解：
            "1. 什么是机器学习
             2. 什么是深度学习
             3. 两者的区别"
        """
        # ========== 构建 Prompt ==========
        prompt = f"""请将以下复合问题拆解成 2-3 个独立的子问题。

                    要求：
                    1. 每个子问题应该独立且完整
                    2. 子问题应该覆盖原问题的所有方面
                    3. 使用换行符分隔子问题
                    4. 每个子问题前加上序号（1. 2. 3.）
                    5. 只返回子问题列表，不要任何解释

                    原始问题：{query}

                    子问题列表："""
        # 说明：
        #   - 使用 LLM 进行分解
        #   - max_tokens=300: 限制输出长度

        return await self._call_llm(prompt, max_tokens=300)

    async def _expand_query(self, query: str) -> str:
        """
        扩展查询
        
        功能说明：
          - 添加同义词和相关表达
          - 提高检索召回率
          - 保持问题的核心意图不变
        
        Args:
            query: 原始查询
        
        Returns:
            扩展后的查询
        
        示例：
            原始："什么是机器学习？"
            扩展："机器学习 定义 概念 含义 人工智能"
            
            原始："如何使用 Python？"
            扩展："Python 使用方法 教程 入门 编程"
        """
        # ========== 构建 Prompt ==========
        prompt = f"""请为以下问题添加相关的同义词和扩展表达，以提高检索效果。

                    要求：
                    1. 保留原始问题的核心内容
                    2. 添加 3-5 个相关的同义词或近义表达
                    3. 使用逗号或顿号分隔
                    4. 不要改变问题的意图
                    5. 只返回扩展后的问题，不要任何解释

                    原始问题：{query}

                    扩展后的问题："""
        # 说明：
        #   - 使用 LLM 进行扩展
        #   - max_tokens=250: 限制输出长度

        return await self._call_llm(prompt, max_tokens=250)

    async def _call_llm(self, prompt: str, max_tokens: int = 200) -> str:
        """
        调用 LLM
        
        功能说明：
          - 使用 OpenRouter API 调用大语言模型
          - 发送 Prompt，获取响应
          - 处理异常和错误
        
        Args:
            prompt: 输入 Prompt
            max_tokens: 最大输出 Token 数
        
        Returns:
            LLM 响应内容（去除首尾空格）
        
        API 参数：
          - model: 使用的模型（从配置读取）
          - messages: 消息列表（用户消息）
          - temperature: 温度（0.3，较低温度保证稳定性）
          - max_tokens: 最大输出 Token 数
        
        请求头：
          - Authorization: API 密钥
          - Content-Type: application/json
          - HTTP-Referer: 应用 URL（用于统计）
          - X-Title: 应用名称（用于统计）
        
        超时设置：
          - 30 秒（避免长时间等待）
        
        异常处理：
          - 捕获所有异常
          - 记录错误日志
          - 返回空字符串（调用方会处理）
        """
        try:
            # ========== 创建异步 HTTP 客户端 ==========
            async with httpx.AsyncClient() as client:
                # ========== 发送 POST 请求 ==========
                response = await client.post(
                    f"{settings.OPENROUTER_BASE_URL}/chat/completions",  # API 端点
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",  # API 密钥
                        "Content-Type": "application/json",  # 内容类型
                        "HTTP-Referer": settings.APP_URL,  # 应用 URL
                        "X-Title": settings.APP_NAME,  # 应用名称
                    },
                    json={
                        "model": self.model,  # 使用的模型
                        "messages": [{"role": "user", "content": prompt}],  # 消息列表
                        "temperature": 0.3,  # 温度（较低温度保证稳定性）
                        "max_tokens": max_tokens,  # 最大输出 Token 数
                    },
                    timeout=30.0,  # 超时时间（30 秒）
                )
                # 说明：
                #   - temperature=0.3: 较低温度，输出更稳定、确定
                #   - max_tokens: 限制输出长度，避免过长响应
                #   - timeout=30.0: 30 秒超时，避免长时间等待

                # ========== 检查响应状态 ==========
                response.raise_for_status()  # 如果状态码不是 2xx，抛出异常

                # ========== 解析响应 ==========
                data = response.json()  # 解析 JSON 响应

                # ========== 提取内容 ==========
                return data["choices"][0]["message"]["content"].strip()
                # 说明：
                #   - data["choices"]: 响应列表（通常只有一个）
                #   - [0]: 第一个响应
                #   - ["message"]["content"]: 消息内容
                #   - .strip(): 去除首尾空格

        except Exception as e:
            # ========== 异常处理 ==========
            logger.error(f"LLM 调用失败: {e}")
            return ""  # 返回空字符串（调用方会处理）


# ============================================================================
# 工厂函数
# ============================================================================

def get_query_rewriter() -> QueryRewriter:
    """
    获取查询重写器实例
    
    功能说明：
      - 创建并返回查询重写器实例
      - 使用默认配置
    
    Returns:
        QueryRewriter: 查询重写器实例
    
    使用示例：
        ```python
        rewriter = get_query_rewriter()
        result = await rewriter.rewrite("这个文档讲了啥呀？")
        ```
    """
    return QueryRewriter()


# ============================================================================
# 查询重写策略详解
# ============================================================================
# 1. 查询标准化（Normalization）
#    - 目的：去除口语化，转换为书面表达
#    - 示例：
#      原始："这个文档讲了啥呀？"
#      标准化："文档主要内容"
#    - 优点：提高检索精度
#    - 缺点：可能丢失部分语义
#
# 2. 查询分解（Decomposition）
#    - 目的：将复合问题拆解为多个子问题
#    - 示例：
#      原始："机器学习和深度学习的区别？"
#      分解："1. 什么是机器学习\n2. 什么是深度学习\n3. 两者的区别"
#    - 优点：提高复杂问题的检索效果
#    - 缺点：增加检索次数
#
# 3. 查询扩展（Expansion）
#    - 目的：添加同义词和相关表达
#    - 示例：
#      原始："什么是机器学习？"
#      扩展："机器学习 定义 概念 含义 人工智能"
#    - 优点：提高召回率
#    - 缺点：可能引入噪声

# ============================================================================
# 复合问题判断规则
# ============================================================================
# 关键词列表：
#   - 连接词：和、与、或者、以及
#   - 对比词：区别、对比、比较
#
# 判断逻辑：
#   - 如果查询包含任意一个关键词 → 复合问题
#   - 否则 → 简单问题
#
# 示例：
#   - "机器学习和深度学习的区别？" → 复合问题
#   - "什么是机器学习？" → 简单问题

# ============================================================================
# LLM 调用参数说明
# ============================================================================
# temperature（温度）：
#   - 范围：0-2
#   - 0.0: 确定性输出（总是选择概率最高的词）
#   - 0.3: 较低温度（稳定、一致）← 本模块使用
#   - 0.7: 中等温度（平衡创造性和稳定性）
#   - 1.0: 标准温度（较高创造性）
#   - 2.0: 高温度（非常随机）
#
# max_tokens（最大 Token 数）：
#   - 标准化：200（短文本）
#   - 分解：300（多个子问题）
#   - 扩展：250（中等长度）
#
# timeout（超时时间）：
#   - 30 秒（避免长时间等待）

# ============================================================================
# 错误处理说明
# ============================================================================
# 1. 查询重写已禁用
#    - 返回原始查询
#    - query_type: "original"
#
# 2. 标准化失败
#    - 使用原始查询
#    - 继续后续步骤
#
# 3. 分解/扩展失败
#    - 使用标准化后的查询
#    - 记录失败步骤
#
# 4. LLM 调用失败
#    - 返回空字符串
#    - 上层处理失败逻辑
#
# 5. 整体失败
#    - 返回原始查询
#    - query_type: "fallback"

# ============================================================================
# 性能优化建议
# ============================================================================
# 1. 缓存重写结果
#    - 缓存常见查询的重写结果
#    - 避免重复调用 LLM
#
# 2. 批量处理
#    - 一次重写多个查询
#    - 减少 API 调用次数
#
# 3. 异步并行
#    - 标准化、分解、扩展并行执行
#    - 减少总耗时
#
# 4. 降级策略
#    - LLM 调用失败时使用规则方法
#    - 保证服务可用性
