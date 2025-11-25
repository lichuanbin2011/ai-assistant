"""
============================================================================
文本分块模块
============================================================================

文件位置：
  rag-service/app/core/chunking.py

文件作用：
  提供文本分块（Text Chunking）功能，将长文本切分为小块

主要功能：
  1. 文本分块 - 将长文本按大小切分
  2. 按页分块 - 按 PDF 页面分块
  3. 递归分块 - 使用多级分隔符智能分块
  4. 重叠分块 - 保留块之间的重叠，保持上下文连贯

分块策略：
  - 递归分块：优先使用段落分隔符，再使用句子分隔符
  - 重叠分块：相邻块之间有重叠，避免信息丢失
  - 长度控制：每个块的大小在指定范围内

技术栈：
  - LangChain Text Splitters（文本分块库）
  - RecursiveCharacterTextSplitter（递归字符分块器）

依赖文件：
  - app/core/config.py（配置管理）

============================================================================
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter  # LangChain 递归分块器
from typing import List, Dict, Any  # 类型注解
from loguru import logger  # 日志记录器

from app.core.config import get_settings  # 配置管理

settings = get_settings()  # 获取配置


# ============================================================================
# 文本分块器类
# ============================================================================

class TextChunker:
    """
    文本分块器
    
    功能说明：
      - 将长文本切分为小块
      - 支持自定义块大小和重叠
      - 支持多级分隔符（段落、句子、标点）
      - 保留元数据（页码、来源等）
    
    分块原理：
      1. 优先使用段落分隔符（\n\n）
      2. 如果块太大，使用句子分隔符（。！？）
      3. 如果还太大，使用标点分隔符（，；）
      4. 如果还太大，使用空格分隔符
      5. 最后使用字符分隔符
    
    重叠原理：
      - 相邻块之间有重叠部分
      - 避免重要信息被切断
      - 保持上下文连贯性
    
    示例：
        ```python
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.chunk_text("长文本...")
        ```
    """

    def __init__(
            self,
            chunk_size: int = None,  # 块大小（字符数）
            chunk_overlap: int = None,  # 重叠大小（字符数）
            separators: List[str] = None  # 分隔符列表
    ):
        """
        初始化分块器
        
        功能说明：
          - 设置块大小和重叠
          - 设置分隔符优先级
          - 创建 LangChain 分块器
        
        Args:
            chunk_size: 块大小（字符数）
                - 默认：从配置读取（通常 500-1000）
                - 推荐：500-1000（中文）、1000-2000（英文）
            
            chunk_overlap: 重叠大小（字符数）
                - 默认：从配置读取（通常 50-100）
                - 推荐：chunk_size 的 10-20%
            
            separators: 分隔符列表
                - 默认：["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
                - 优先级：从左到右递减
        
        分隔符说明：
          - "\n\n": 段落分隔符（最高优先级）
          - "\n": 行分隔符
          - "。！？": 句子结束符
          - "；": 分句符
          - "，": 逗号
          - " ": 空格
          - "": 字符（最低优先级）
        
        块大小建议：
          - 小块（200-500）：适合精确检索
          - 中块（500-1000）：平衡检索和上下文
          - 大块（1000-2000）：保留更多上下文
        
        重叠建议：
          - 小重叠（50-100）：节省存储空间
          - 中重叠（100-200）：平衡连贯性和空间
          - 大重叠（200+）：最大化连贯性
        """
        # ========== 1. 设置参数 ==========
        self.chunk_size = chunk_size or settings.CHUNK_SIZE  # 块大小（默认从配置读取）
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP  # 重叠大小（默认从配置读取）
        self.separators = separators or [  # 分隔符列表（默认值）
            "\n\n",  # 段落分隔符（优先级最高）
            "\n",    # 行分隔符
            "。",    # 句号
            "！",    # 感叹号
            "？",    # 问号
            "；",    # 分号
            "，",    # 逗号
            " ",     # 空格
            ""       # 字符（优先级最低）
        ]

        # ========== 2. 创建 LangChain 分块器 ==========
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,  # 块大小
            chunk_overlap=self.chunk_overlap,  # 重叠大小
            separators=self.separators,  # 分隔符列表
            length_function=len,  # 长度计算函数（使用字符数）
        )
        # 说明：
        #   - RecursiveCharacterTextSplitter: LangChain 的递归分块器
        #   - 递归策略：从高优先级分隔符开始尝试，如果块太大则使用低优先级分隔符
        #   - length_function=len: 使用字符数计算长度（中文和英文都适用）

        logger.info(f"文本分块器初始化: chunk_size={self.chunk_size}, overlap={self.chunk_overlap}")

    def chunk_text(
            self,
            text: str,  # 输入文本
            metadata: Dict[str, Any] = None  # 元数据（页码、来源等）
    ) -> List[Dict[str, Any]]:
        """
        分块文本
        
        功能说明：
          - 将长文本切分为小块
          - 保留元数据
          - 添加块索引
        
        分块流程：
          1. 验证输入（检查是否为空）
          2. 执行分块（使用 LangChain 分块器）
          3. 处理结果（添加索引和元数据）
          4. 返回分块列表
        
        Args:
            text: 输入文本
                - 类型：字符串
                - 要求：非空
            
            metadata: 元数据（可选）
                - 类型：字典
                - 示例：{"page_number": 1, "source": "pdf"}

        Returns:
            分块结果列表：
            [
                {
                    "chunk_index": 0,
                    "content": "文本内容...",
                    "char_count": 500,
                    "metadata": {"page_number": 1, "source": "pdf"}
                },
                {
                    "chunk_index": 1,
                    "content": "文本内容...",
                    "char_count": 480,
                    "metadata": {"page_number": 1, "source": "pdf"}
                }
            ]
        
        字段说明：
          - chunk_index: 块索引（从 0 开始）
          - content: 文本内容
          - char_count: 字符数
          - metadata: 元数据（页码、来源等）
        
        使用示例：
            ```python
            chunker = TextChunker()
            chunks = chunker.chunk_text(
                text="长文本...",
                metadata={"page_number": 1}
            )
            ```
        
        Raises:
            ValueError: 文本分块失败
        """
        # ========== 1. 验证输入 ==========
        if not text or not text.strip():
            logger.warning("输入文本为空")
            return []

        logger.info(f"开始文本分块，原始长度: {len(text)}")

        try:
            # ========== 2. 执行分块 ==========
            docs = self.splitter.create_documents([text], [metadata or {}])
            # 说明：
            #   - create_documents: LangChain 的分块方法
            #   - 参数 1：文本列表（这里只有一个文本）
            #   - 参数 2：元数据列表（与文本一一对应）
            #   - 返回：Document 对象列表
            #     [
            #       Document(page_content="文本内容", metadata={...}),
            #       Document(page_content="文本内容", metadata={...})
            #     ]

            # ========== 3. 处理结果 ==========
            chunks = []
            for i, doc in enumerate(docs):
                chunk = {
                    "chunk_index": i,  # 块索引（从 0 开始）
                    "content": doc.page_content,  # 文本内容
                    "char_count": len(doc.page_content),  # 字符数
                    "metadata": {**doc.metadata, **(metadata or {})},  # 合并元数据
                }
                chunks.append(chunk)
            # 说明：
            #   - chunk_index: 块的顺序索引
            #   - content: 块的文本内容
            #   - char_count: 块的字符数（用于统计和验证）
            #   - metadata: 合并 LangChain 的元数据和用户提供的元数据

            # ========== 4. 记录日志 ==========
            logger.info(f"分块完成: {len(chunks)} 个块")
            logger.debug(f"平均块大小: {sum(c['char_count'] for c in chunks) / len(chunks):.0f} 字符")

            return chunks

        except Exception as e:
            # ========== 5. 异常处理 ==========
            logger.error(f"分块失败: {e}")
            raise ValueError(f"文本分块失败: {str(e)}")

    def chunk_by_pages(
            self,
            page_texts: List[Dict[str, Any]]  # 页面文本列表
    ) -> List[Dict[str, Any]]:
        """
        按页分块
        
        功能说明：
          - 将 PDF 的每一页分别分块
          - 保留页码信息
          - 合并所有页的分块
        
        分块流程：
          1. 遍历每一页
          2. 对每页的文本进行分块
          3. 添加页码信息到元数据
          4. 合并所有分块
        
        Args:
            page_texts: 页面文本列表
                格式：
                [
                    {"page": 1, "text": "第一页内容..."},
                    {"page": 2, "text": "第二页内容..."},
                    {"page": 3, "text": "第三页内容..."}
                ]

        Returns:
            分块结果列表：
            [
                {
                    "chunk_index": 0,
                    "content": "第一页第一块...",
                    "char_count": 500,
                    "metadata": {"page_number": 1, "source": "pdf"}
                },
                {
                    "chunk_index": 1,
                    "content": "第一页第二块...",
                    "char_count": 480,
                    "metadata": {"page_number": 1, "source": "pdf"}
                },
                {
                    "chunk_index": 2,
                    "content": "第二页第一块...",
                    "char_count": 520,
                    "metadata": {"page_number": 2, "source": "pdf"}
                }
            ]
        
        使用示例：
            ```python
            chunker = TextChunker()
            page_texts = [
                {"page": 1, "text": "第一页内容..."},
                {"page": 2, "text": "第二页内容..."}
            ]
            chunks = chunker.chunk_by_pages(page_texts)
            ```
        
        注意事项：
          - chunk_index 是全局索引（跨页连续）
          - page_number 是页码（从 1 开始）
          - 空页会被跳过
        """
        all_chunks = []  # 所有分块的列表

        # ========== 1. 遍历每一页 ==========
        for page_data in page_texts:
            page_num = page_data.get("page", 0)  # 页码（从 1 开始）
            text = page_data.get("text", "")  # 页面文本

            # ========== 2. 跳过空页 ==========
            if not text.strip():
                continue

            # ========== 3. 分块并添加页码信息 ==========
            chunks = self.chunk_text(
                text,
                metadata={"page_number": page_num, "source": "pdf"}
            )
            # 说明：
            #   - 对每页的文本单独分块
            #   - 添加页码信息到元数据
            #   - source="pdf" 表示来源是 PDF

            # ========== 4. 合并分块 ==========
            all_chunks.extend(chunks)

        logger.info(f"按页分块完成: {len(page_texts)} 页 → {len(all_chunks)} 块")

        return all_chunks


# ============================================================================
# 工厂函数
# ============================================================================

def get_chunker() -> TextChunker:
    """
    获取分块器实例
    
    功能说明：
      - 创建并返回文本分块器实例
      - 使用默认配置
    
    Returns:
        TextChunker: 文本分块器实例
    
    使用示例：
        ```python
        chunker = get_chunker()
        chunks = chunker.chunk_text("长文本...")
        ```
    """
    return TextChunker()


# ============================================================================
# 分块策略详解
# ============================================================================
# 1. 递归分块（Recursive Chunking）
#    - 原理：从高优先级分隔符开始尝试，如果块太大则使用低优先级分隔符
#    - 优点：保持语义完整性，避免切断句子
#    - 缺点：可能产生大小不均匀的块
#
# 2. 固定大小分块（Fixed-size Chunking）
#    - 原理：按固定字符数切分
#    - 优点：块大小均匀，便于管理
#    - 缺点：可能切断句子，破坏语义
#
# 3. 语义分块（Semantic Chunking）
#    - 原理：根据语义边界切分（段落、章节）
#    - 优点：保持语义完整性
#    - 缺点：块大小不均匀，实现复杂
#
# 4. 重叠分块（Overlapping Chunking）
#    - 原理：相邻块之间有重叠部分
#    - 优点：避免信息丢失，保持上下文连贯
#    - 缺点：增加存储空间

# ============================================================================
# 分隔符优先级说明
# ============================================================================
# 优先级从高到低：
#   1. "\n\n" - 段落分隔符（最高优先级）
#      - 用途：分隔段落
#      - 示例：第一段\n\n第二段
#
#   2. "\n" - 行分隔符
#      - 用途：分隔行
#      - 示例：第一行\n第二行
#
#   3. "。！？" - 句子结束符
#      - 用途：分隔句子
#      - 示例：第一句。第二句。
#
#   4. "；" - 分句符
#      - 用途：分隔分句
#      - 示例：前半句；后半句。
#
#   5. "，" - 逗号
#      - 用途：分隔短语
#      - 示例：前半句，后半句。
#
#   6. " " - 空格
#      - 用途：分隔单词
#      - 示例：word1 word2
#
#   7. "" - 字符（最低优先级）
#      - 用途：按字符切分
#      - 示例：a|b|c|d

# ============================================================================
# 块大小和重叠建议
# ============================================================================
# 中文文本：
#   - 块大小：500-1000 字符
#   - 重叠：50-100 字符（10-20%）
#
# 英文文本：
#   - 块大小：1000-2000 字符
#   - 重叠：100-200 字符（10-20%）
#
# 代码文本：
#   - 块大小：200-500 字符
#   - 重叠：20-50 字符（10%）
#
# 长文档：
#   - 块大小：1000-2000 字符
#   - 重叠：100-200 字符（10%）

# ============================================================================
# 性能优化建议
# ============================================================================
# 1. 批量处理
#    - 一次处理多个文本
#    - 减少初始化开销
#
# 2. 缓存分块器
#    - 复用分块器实例
#    - 避免重复创建
#
# 3. 并行分块
#    - 多线程/多进程处理
#    - 提高处理速度
#
# 4. 预处理文本
#    - 去除多余空格
#    - 统一换行符
#    - 提高分块质量
