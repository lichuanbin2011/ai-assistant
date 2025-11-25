"""
============================================================================
请求数据模型 - 支持多模态（文本 + 图片）
============================================================================

文件位置：
  llm-service/app/models/requests.py

文件作用：
  定义 API 请求的数据模型，支持多模态输入（文本 + 图片）

主要功能：
  1. 数据验证 - 使用 Pydantic 自动验证请求数据
  2. 类型注解 - 提供完整的类型提示
  3. 多模态支持 - 支持文本、图片混合输入
  4. 文档生成 - 自动生成 Swagger 文档示例

模型结构：
  GenerateRequest（生成请求）
    └── messages: List[Message]（消息列表）
          └── content: ContentType（内容）
                ├── 纯文本：str
                └── 多模态：List[TextContent | ImageContent]

支持的内容类型：
  - 纯文本消息：content = "你好"
  - 多模态消息：content = [TextContent, ImageContent]

技术栈：
  - Pydantic（数据验证）
  - Python Type Hints（类型注解）

使用场景：
  - 纯文本对话
  - 图片识别（OCR、物体检测）
  - 图文混合对话

依赖文件：
  - app/api/v1/generate.py（生成接口）

============================================================================
"""
from pydantic import BaseModel, Field, field_validator  # Pydantic 数据验证
from typing import List, Optional, Literal, Union  # 类型注解

# ====================  新增：多模态内容类型定义 ====================

class TextContent(BaseModel):
    """
    文本内容模型
    
    用于多模态消息中的文本部分
    
    示例：
        {
            "type": "text",
            "text": "这是什么？"
        }
    """
    type: Literal["text"] = Field(default="text", description="内容类型")  # 固定值 "text"（用于区分内容类型）
    text: str = Field(..., description="文本内容")  # 文本内容（必填）

    class Config:
        # Swagger 文档示例
        json_schema_extra = {
            "example": {
                "type": "text",
                "text": "这是什么？"
            }
        }


class ImageUrl(BaseModel):
    """
    图片 URL 模型
    
    支持的 URL 格式：
      - HTTP/HTTPS URL：https://example.com/image.jpg
      - Data URI：data:image/png;base64,iVBORw0KGgo...
    
    示例：
        {
            "url": "data:image/png;base64,iVBORw0KGgo...",
            "detail": "auto"
        }
    """
    url: str = Field(..., description="图片 URL（支持 http/https/data URI）")  # 图片地址（必填）
    detail: Optional[Literal["auto", "low", "high"]] = Field(
        default="auto",  # 默认自动选择细节级别
        description="图片细节级别"
    )
    # detail 参数说明：
    #   - auto: 自动选择（推荐）
    #   - low: 低分辨率（快速，节省 token）
    #   - high: 高分辨率（详细，消耗更多 token）

    class Config:
        # Swagger 文档示例
        json_schema_extra = {
            "example": {
                "url": "data:image/png;base64,iVBORw0KGgo...",
                "detail": "auto"
            }
        }


class ImageContent(BaseModel):
    """
    图片内容模型
    
    用于多模态消息中的图片部分
    
    示例：
        {
            "type": "image_url",
            "image_url": {
                "url": "data:image/png;base64,iVBORw0KGgo..."
            }
        }
    """
    type: Literal["image_url"] = Field(default="image_url", description="内容类型")  # 固定值 "image_url"（用于区分内容类型）
    image_url: ImageUrl = Field(..., description="图片 URL 对象")  # 图片 URL 对象（必填）

    class Config:
        # Swagger 文档示例
        json_schema_extra = {
            "example": {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,iVBORw0KGgo..."
                }
            }
        }


#  定义内容类型：可以是字符串或多模态数组
# Union 表示"或"关系，即 content 可以是以下两种类型之一：
#   1. str：纯文本消息（向后兼容）
#   2. List[Union[TextContent, ImageContent]]：多模态消息（文本 + 图片）
ContentType = Union[str, List[Union[TextContent, ImageContent]]]

# ====================  修改：Message 模型支持多模态 ====================

class Message(BaseModel):
    """
    消息模型 - 支持多模态（文本 + 图片）
    
    支持两种格式：
      1. 纯文本消息（向后兼容）：
         {
             "role": "user",
             "content": "你好"
         }
      
      2. 多模态消息（文本 + 图片）：
         {
             "role": "user",
             "content": [
                 {"type": "text", "text": "这是什么？"},
                 {"type": "image_url", "image_url": {"url": "..."}}
             ]
         }
    """
    role: Literal["user", "assistant", "system"] = Field(..., description="角色")  # 消息角色（必填）
    # role 说明：
    #   - user: 用户消息
    #   - assistant: AI 助手消息
    #   - system: 系统提示词
    
    #  修改：content 字段支持字符串或多模态数组
    content: ContentType = Field(..., description="消息内容（字符串或多模态数组）")  # 消息内容（必填）

    class Config:
        # Swagger 文档示例（提供多个示例）
        json_schema_extra = {
            "examples": [
                # 示例 1：纯文本消息（传统格式）
                {
                    "role": "user",
                    "content": "你好，请介绍一下自己"
                },
                # 示例 2：多模态消息（文本 + 图片）
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "这张图片里是什么？"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64,iVBORw0KGgo..."
                            }
                        }
                    ]
                }
            ]
        }


# ==================== GenerateRequest 保持不变 ====================

class GenerateRequest(BaseModel):
    """
    生成请求模型
    
    定义 LLM 生成接口的请求参数
    
    功能说明：
      - 支持多轮对话（messages 列表）
      - 支持多模态输入（文本 + 图片）
      - 支持自定义生成参数（温度、最大长度等）
    
    示例：
        {
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "model": "openai/gpt-4o",
            "temperature": 0.7,
            "stream": true
        }
    """
    messages: List[Message] = Field(..., min_length=1, description="对话历史")  # 消息列表（必填，至少 1 条）
    model: Optional[str] = Field(default=None, description="模型名称")  # 模型名称（可选，默认使用配置中的模型）
    provider: Optional[Literal["openrouter"]] = Field(
        default="openrouter",  # 默认使用 OpenRouter
        description="LLM 提供商"
    )
    # provider 说明：
    #   - openrouter: OpenRouter 平台（支持多种模型）
    #   - 未来可扩展：anthropic、openai、google 等
    
    temperature: Optional[float] = Field(default=None, ge=0, le=2, description="温度参数")  # 温度（可选，0-2）
    # temperature 说明：
    #   - 0: 确定性输出（适合事实性问答）
    #   - 0.7: 平衡（默认值）
    #   - 2: 高随机性（适合创意写作）
    
    max_tokens: Optional[int] = Field(default=None, ge=1, description="最大 token 数")  # 最大生成长度（可选）
    stream: bool = Field(default=True, description="是否流式返回")  # 是否启用流式传输（默认启用）

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v):
        """
        验证消息列表
        
        验证规则：
          1. 消息列表不能为空
          2. 最后一条消息必须是用户消息（确保 AI 有内容可回复）
        
        Args:
            v: 消息列表
        
        Returns:
            验证通过的消息列表
        
        Raises:
            ValueError: 验证失败时抛出异常
        """
        # 规则 1：消息列表不能为空
        if not v:
            raise ValueError("消息列表不能为空")
        
        # 规则 2：最后一条消息必须是用户消息
        # 原因：AI 需要根据用户消息生成回复
        if v[-1].role != "user":
            raise ValueError("最后一条消息必须是用户消息")
        
        return v

    class Config:
        # Swagger 文档示例（提供多个示例）
        json_schema_extra = {
            "examples": [
                # 示例 1：纯文本对话
                {
                    "messages": [
                        {"role": "user", "content": "你好"}
                    ],
                    "model": "openai/gpt-4o",
                    "provider": "openrouter",
                    "temperature": 0.7,
                    "stream": True
                },
                #  新增：示例 2：多模态对话（文本 + 图片）
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "请分析这张图片"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": "data:image/png;base64,iVBORw0KGgo..."
                                    }
                                }
                            ]
                        }
                    ],
                    "model": "openai/gpt-4o",
                    "provider": "openrouter",
                    "temperature": 0.7,
                    "stream": True
                }
            ]
        }


# ============================================================================
# 使用示例
# ============================================================================
# 示例 1：纯文本对话
# request = GenerateRequest(
#     messages=[
#         Message(role="user", content="你好")
#     ],
#     model="openai/gpt-4o",
#     stream=True
# )

# 示例 2：多模态对话（文本 + 图片）
# request = GenerateRequest(
#     messages=[
#         Message(
#             role="user",
#             content=[
#                 TextContent(text="这是什么？"),
#                 ImageContent(
#                     image_url=ImageUrl(
#                         url="data:image/png;base64,iVBORw0KGgo..."
#                     )
#                 )
#             ]
#         )
#     ],
#     model="openai/gpt-4o",
#     stream=True
# )

# ============================================================================
# 多模态支持说明
# ============================================================================
# 支持的模型：
#   - openai/gpt-4o（推荐，视觉能力强）
#   - openai/gpt-4-vision-preview
#   - anthropic/claude-3-opus
#   - google/gemini-pro-vision
#
# 图片格式：
#   - JPEG、PNG、GIF、WebP
#   - 最大尺寸：20MB
#   - 推荐分辨率：2048x2048
#
# Data URI 格式：
#   data:image/png;base64,iVBORw0KGgo...
#   data:image/jpeg;base64,/9j/4AAQSkZJRg...
