"""
============================================================================
PDF 处理服务模块（完全修复版 - 2025-11-22）
============================================================================

文件位置：
  rag-service/app/services/pdf_processor.py

文件作用：
  负责 PDF 文件的完整处理流程，是 RAG 系统的"文档处理"核心模块

主要功能：
  1. PDF 解析 - 提取 PDF 文本内容（支持多种解析库）
  2. 文本分块 - 将长文本切分成适合向量化的小块
  3. 向量化 - 将文本块转换为向量（调用 EmbeddingService）
  4. 数据库存储 - 保存文本块和向量到数据库
  5. 状态管理 - 更新 PDF 处理状态（processing/ready/failed）

技术栈：
  - pdfplumber（主要 PDF 解析库，功能强大）
  - PyPDF2（备用 PDF 解析库）
  - PostgreSQL + pgvector（向量数据库）

依赖文件：
  - app/core/rag/chunking.py（文本分块）
  - app/services/embedding.py（向量化）
  - app/core/database.py（数据库）

数据库表：
  - pdfs（PDF 文件记录）
  - document_chunks（文档分块 + 向量）

修复内容（2025-11-22）：
  1. ✅ 所有数据库操作改为命名参数（:param_name）
  2. ✅ 字段名使用双引号包裹驼峰命名（"updatedAt", "createdAt"）
  3. ✅ metadata 转换为 JSON 字符串
  4. ✅ 添加详细错误日志
  5. ✅ 修复批量插入逻辑
  6. ✅ 添加 UUID 生成

处理流程：
  用户上传 PDF → 解析文本 → 分块 → 向量化 → 存储 → 更新状态
                  ↓          ↓       ↓        ↓        ↓
                pdfplumber  chunker embedding database  pdfs.status=ready

使用示例：
    ```python
    from app.services.pdf_processor import get_pdf_processor
    
    processor = get_pdf_processor()
    
    # 处理 PDF
    result = await processor.process_pdf(
        file_path="/uploads/document.pdf",
        pdf_id="123e4567-e89b-12d3-a456-426614174000"
    )
    # 返回: {
    #     "success": True,
    #     "pdf_id": "...",
    #     "total_pages": 50,
    #     "total_chunks": 120
    # }
    ```

============================================================================
"""
import uuid  # ✅ 新增：用于生成 UUID（通用唯一标识符）
import io  # 用于处理字节流（BytesIO）
import json  # ✅ 新增：用于 JSON 序列化（metadata 转换）
from typing import List, Dict, Any, Optional
from pathlib import Path  # 用于文件路径操作
from loguru import logger  # 日志记录

# ============================================================================
# PDF 解析库导入（支持多种库，提高兼容性）
# ============================================================================

try:
    import PyPDF2  # 备用 PDF 解析库（轻量级）
    PYPDF2_AVAILABLE = True  # 标记 PyPDF2 可用
except ImportError:
    logger.warning("PyPDF2 未安装，PDF 处理功能将不可用")
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber  # 主要 PDF 解析库（功能强大，推荐）
    PDFPLUMBER_AVAILABLE = True  # 标记 pdfplumber 可用
except ImportError:
    logger.warning("pdfplumber 未安装，将使用 PyPDF2 作为备选")
    PDFPLUMBER_AVAILABLE = False

# ============================================================================
# 导入依赖服务
# ============================================================================

from app.core.rag.chunking import get_chunker  # 文本分块服务
from app.services.embedding import get_embedding_service  # 向量化服务
from app.core.database import get_database  # 数据库服务


class PDFProcessor:
    """
    PDF 处理器类
    
    职责：
        - 解析 PDF 文件（提取文本）
        - 文本分块（切分成小块）
        - 向量化（转换为向量）
        - 数据库存储（保存文本和向量）
        - 状态管理（更新处理状态）
    
    属性：
        chunker: 文本分块器（ChunkingService）
        embedding_service: 向量化服务（EmbeddingService）
        db: 数据库连接（Database）
    
    支持的 PDF 库：
        - pdfplumber（主要，功能强大）
        - PyPDF2（备用，轻量级）
    """

    def __init__(self):
        """
        初始化 PDF 处理器
        
        工作流程：
            1. 初始化文本分块器
            2. 初始化向量化服务
            3. 初始化数据库连接
            4. 检查 PDF 解析库是否可用
            5. 记录初始化信息
        
        Raises:
            RuntimeError: 如果没有安装任何 PDF 解析库
        """
        # 初始化依赖服务
        self.chunker = get_chunker()  # 文本分块器
        self.embedding_service = get_embedding_service()  # 向量化服务
        self.db = get_database()  # 数据库连接

        # 检查 PDF 解析库是否可用
        if not PYPDF2_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            raise RuntimeError("未安装 PDF 处理库（PyPDF2 或 pdfplumber）")

        # 记录初始化信息
        logger.info(
            f"PDF 处理器初始化完成 (PyPDF2={PYPDF2_AVAILABLE}, "
            f"pdfplumber={PDFPLUMBER_AVAILABLE})"
        )

    async def process_pdf(
        self,
        file_path: str,
        pdf_id: str,
        use_pdfplumber: bool = True
    ) -> Dict[str, Any]:
        """
        处理 PDF 文件（完整流程）
        
        这是 PDF 处理的主入口函数，完成从文件到向量的全流程
        
        工作流程：
            1. 解析 PDF（提取文本）
            2. 文本分块（切分成小块）
            3. 批量向量化（转换为向量）
            4. 存储到数据库（保存文本和向量）
            5. 更新 PDF 状态（标记为 ready）
        
        流程图：
            PDF 文件 → 解析 → 分块 → 向量化 → 存储 → 更新状态
                       ↓      ↓       ↓        ↓        ↓
                    page_texts chunks embeddings DB    status=ready
        
        Args:
            file_path: PDF 文件路径（绝对路径）
                      例如："/app/uploads/document.pdf"
            
            pdf_id: PDF 记录 ID（数据库中的主键）
                   例如："123e4567-e89b-12d3-a456-426614174000"
            
            use_pdfplumber: 是否优先使用 pdfplumber（默认 True）
                           - True：优先使用 pdfplumber，失败时回退到 PyPDF2
                           - False：直接使用 PyPDF2
        
        Returns:
            处理结果字典：
            {
                "success": True,                # 是否成功
                "pdf_id": "...",                # PDF ID
                "total_pages": 50,              # 总页数
                "total_chunks": 120,            # 总分块数
                "cache_stats": {...}            # 缓存统计（可选）
            }
        
        Raises:
            ValueError: 处理失败时抛出（包含错误信息）
        
        数据库变化：
            - pdfs 表：status 从 'processing' 变为 'ready'
            - document_chunks 表：插入所有分块和向量
        
        示例：
            result = await process_pdf(
                file_path="/uploads/document.pdf",
                pdf_id="123e4567-e89b-12d3-a456-426614174000"
            )
            # 返回: {"success": True, "total_pages": 50, "total_chunks": 120}
        """
        logger.info(f"开始处理 PDF: {file_path}")

        try:
            # ================================================================
            # 步骤1：解析 PDF（提取文本）
            # ================================================================
            # 调用 parse_pdf() 提取 PDF 文本
            # 返回：{"text": "全文", "total_pages": 50, "page_texts": [...]}
            pdf_data = await self.parse_pdf(file_path, use_pdfplumber)

            logger.info(
                f"PDF 解析完成: {pdf_data['total_pages']} 页, "
                f"{len(pdf_data['text'])} 字符"
            )

            # ================================================================
            # 步骤2：文本分块（切分成小块）
            # ================================================================
            # 调用 chunker.chunk_by_pages() 按页分块
            # 返回：[{"content": "...", "chunk_index": 0, "metadata": {...}}, ...]
            chunks = self.chunker.chunk_by_pages(pdf_data['page_texts'])

            logger.info(f"文本分块完成: {len(chunks)} 个块")

            # ================================================================
            # 步骤3：批量向量化（转换为向量）
            # ================================================================
            # 提取所有分块的文本内容
            texts = [chunk['content'] for chunk in chunks]

            # 调用 embedding_service.embed_batch() 批量向量化
            # 返回：{"embeddings": [[...], [...]], "cache_stats": {...}}
            result = await self.embedding_service.embed_batch(
                texts=texts,
                show_progress=True  # 显示进度条
            )

            embeddings = result['embeddings']  # 提取向量列表

            logger.info(f"向量化完成: {len(embeddings)} 个向量")

            # ================================================================
            # 步骤4：存储到数据库（保存文本和向量）
            # ================================================================
            # 调用 _save_chunks_to_db() 保存所有分块和向量
            await self._save_chunks_to_db(
                pdf_id=pdf_id,
                chunks=chunks,
                embeddings=embeddings
            )

            logger.info(f"数据库存储完成")

            # ================================================================
            # 步骤5：更新 PDF 状态（标记为 ready）
            # ================================================================
            # 🔧 修复位置 1：使用命名参数 + 正确的字段名
            # 更新 pdfs 表：status='ready', totalPages=50, totalChunks=120
            await self.db.execute(
                """
                UPDATE pdfs
                SET status = :status,
                    "totalPages" = :total_pages,
                    "totalChunks" = :total_chunks,
                    "updatedAt" = NOW()
                WHERE id = :pdf_id
                """,
                status='ready',  # 状态改为 ready（可查询）
                total_pages=pdf_data['total_pages'],  # 总页数
                total_chunks=len(chunks),  # 总分块数
                pdf_id=pdf_id  # PDF ID
            )

            logger.info(f"PDF 处理完成: {pdf_id}")

            # 返回处理结果
            return {
                "success": True,
                "pdf_id": pdf_id,
                "total_pages": pdf_data['total_pages'],
                "total_chunks": len(chunks),
                "cache_stats": result.get('cache_stats'),  # 缓存统计（可选）
            }

        except Exception as e:
            # ================================================================
            # 错误处理：记录错误并更新状态为 failed
            # ================================================================
            logger.error(f"PDF 处理失败: {e}")
            logger.exception(e)  # ✅ 添加详细堆栈信息

            # 🔧 修复位置 2：使用命名参数 + 正确的字段名
            # 更新 pdfs 表：status='failed', errorMessage="..."
            try:
                await self.db.execute(
                    """
                    UPDATE pdfs
                    SET status = :status,
                        "errorMessage" = :error_message,
                        "updatedAt" = NOW()
                    WHERE id = :pdf_id
                    """,
                    status='failed',  # 状态改为 failed
                    error_message=str(e),  # 错误信息
                    pdf_id=pdf_id  # PDF ID
                )
            except Exception as update_error:
                logger.error(f"更新失败状态时出错: {update_error}")

            # 抛出异常（让调用者知道失败）
            raise ValueError(f"PDF 处理失败: {str(e)}")

    async def parse_pdf(
        self,
        file_path: str,
        use_pdfplumber: bool = True
    ) -> Dict[str, Any]:
        """
        解析 PDF 文件（提取文本）
        
        功能说明：
            从 PDF 文件中提取文本内容，支持多种解析库
            优先使用 pdfplumber（功能强大），失败时回退到 PyPDF2
        
        工作流程：
            1. 检查文件是否存在
            2. 检查文件扩展名是否为 .pdf
            3. 尝试使用 pdfplumber 解析
            4. 如果失败，回退到 PyPDF2
            5. 返回解析结果
        
        Args:
            file_path: PDF 文件路径（绝对路径）
                      例如："/app/uploads/document.pdf"
            
            use_pdfplumber: 是否优先使用 pdfplumber（默认 True）
                           - True：优先 pdfplumber，失败时回退
                           - False：直接使用 PyPDF2
        
        Returns:
            解析结果字典：
            {
                "text": "全文内容...",           # 完整文本（所有页拼接）
                "total_pages": 50,               # 总页数
                "page_texts": [                  # 每页的文本
                    {"page": 1, "text": "..."},
                    {"page": 2, "text": "..."},
                    ...
                ],
                "parser": "pdfplumber"           # 使用的解析器
            }
        
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不是 PDF 文件
            RuntimeError: 没有可用的 PDF 解析库
        
        示例：
            result = await parse_pdf("/uploads/document.pdf")
            print(result['total_pages'])  # 50
            print(result['page_texts'][0])  # {"page": 1, "text": "..."}
        """
        path = Path(file_path)  # 创建 Path 对象

        # 检查文件是否存在
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检查文件扩展名是否为 .pdf
        if not path.suffix.lower() == '.pdf':
            raise ValueError(f"不是 PDF 文件: {file_path}")

        # 优先使用 pdfplumber（更强大）
        if use_pdfplumber and PDFPLUMBER_AVAILABLE:
            try:
                return await self._parse_with_pdfplumber(file_path)
            except Exception as e:
                logger.warning(f"pdfplumber 解析失败，回退到 PyPDF2: {e}")

        # 回退到 PyPDF2
        if PYPDF2_AVAILABLE:
            return await self._parse_with_pypdf2(file_path)

        # 如果两个库都不可用，抛出异常
        raise RuntimeError("没有可用的 PDF 解析库")

    async def _parse_with_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        """
        使用 pdfplumber 解析 PDF
        
        pdfplumber 特点：
            - 功能强大，支持表格、图像提取
            - 文本提取准确率高
            - 支持复杂布局的 PDF
        
        工作流程：
            1. 打开 PDF 文件
            2. 遍历每一页
            3. 提取每页的文本
            4. 拼接成完整文本
            5. 返回结果
        
        Args:
            file_path: PDF 文件路径
        
        Returns:
            解析结果（格式同 parse_pdf()）
        """
        logger.debug(f"使用 pdfplumber 解析: {file_path}")

        page_texts = []  # 每页的文本列表
        full_text = []  # 完整文本列表（用于拼接）

        # 打开 PDF 文件
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)  # 获取总页数

            # 遍历每一页
            for i, page in enumerate(pdf.pages):
                try:
                    # 提取文本（如果为空则返回 ""）
                    text = page.extract_text() or ""

                    # 保存每页的文本
                    page_texts.append({
                        "page": i + 1,  # 页码（从 1 开始）
                        "text": text  # 文本内容
                    })

                    # 添加到完整文本列表
                    full_text.append(text)

                except Exception as e:
                    # 如果某一页解析失败，记录警告并继续
                    logger.warning(f"解析第 {i + 1} 页失败: {e}")
                    page_texts.append({
                        "page": i + 1,
                        "text": ""  # 空文本
                    })

        # 返回解析结果
        return {
            "text": "\n\n".join(full_text),  # 用两个换行符拼接所有页
            "total_pages": total_pages,
            "page_texts": page_texts,
            "parser": "pdfplumber"  # 标记使用的解析器
        }

    async def _parse_with_pypdf2(self, file_path: str) -> Dict[str, Any]:
        """
        使用 PyPDF2 解析 PDF
        
        PyPDF2 特点：
            - 轻量级，依赖少
            - 适合简单的文本提取
            - 对复杂布局支持较弱
        
        工作流程：
            1. 打开 PDF 文件（二进制模式）
            2. 创建 PdfReader 对象
            3. 遍历每一页
            4. 提取每页的文本
            5. 拼接成完整文本
            6. 返回结果
        
        Args:
            file_path: PDF 文件路径
        
        Returns:
            解析结果（格式同 parse_pdf()）
        """
        logger.debug(f"使用 PyPDF2 解析: {file_path}")

        page_texts = []  # 每页的文本列表
        full_text = []  # 完整文本列表

        # 打开 PDF 文件（二进制模式）
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)  # 创建 PDF 读取器
            total_pages = len(reader.pages)  # 获取总页数

            # 遍历每一页
            for i, page in enumerate(reader.pages):
                try:
                    # 提取文本
                    text = page.extract_text() or ""

                    # 保存每页的文本
                    page_texts.append({
                        "page": i + 1,
                        "text": text
                    })

                    # 添加到完整文本列表
                    full_text.append(text)

                except Exception as e:
                    # 如果某一页解析失败，记录警告并继续
                    logger.warning(f"解析第 {i + 1} 页失败: {e}")
                    page_texts.append({
                        "page": i + 1,
                        "text": ""
                    })

        # 返回解析结果
        return {
            "text": "\n\n".join(full_text),
            "total_pages": total_pages,
            "page_texts": page_texts,
            "parser": "PyPDF2"  # 标记使用的解析器
        }

    async def parse_pdf_from_bytes(
        self,
        pdf_bytes: bytes,
        use_pdfplumber: bool = True
    ) -> Dict[str, Any]:
        """
        从字节流解析 PDF
        
        功能说明：
            直接从内存中的字节流解析 PDF（不需要保存到文件）
            适用于上传的文件（FastAPI UploadFile）
        
        工作流程：
            1. 尝试使用 pdfplumber 解析字节流
            2. 如果失败，回退到 PyPDF2
            3. 返回解析结果
        
        Args:
            pdf_bytes: PDF 文件字节流（bytes 类型）
                      例如：await file.read() 的结果
            
            use_pdfplumber: 是否优先使用 pdfplumber
        
        Returns:
            解析结果（格式同 parse_pdf()）
        
        示例：
            # FastAPI 中使用
            @app.post("/upload")
            async def upload(file: UploadFile):
                pdf_bytes = await file.read()
                result = await parse_pdf_from_bytes(pdf_bytes)
                return result
        """
        logger.debug(f"从字节流解析 PDF: {len(pdf_bytes)} 字节")

        # 优先使用 pdfplumber
        if use_pdfplumber and PDFPLUMBER_AVAILABLE:
            try:
                return await self._parse_bytes_with_pdfplumber(pdf_bytes)
            except Exception as e:
                logger.warning(f"pdfplumber 解析失败，回退到 PyPDF2: {e}")

        # 回退到 PyPDF2
        if PYPDF2_AVAILABLE:
            return await self._parse_bytes_with_pypdf2(pdf_bytes)

        raise RuntimeError("没有可用的 PDF 解析库")

    async def _parse_bytes_with_pdfplumber(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        使用 pdfplumber 解析字节流
        
        工作流程：
            1. 将 bytes 包装成 BytesIO 对象（模拟文件）
            2. 使用 pdfplumber.open() 打开
            3. 提取文本（同 _parse_with_pdfplumber）
        
        Args:
            pdf_bytes: PDF 字节流
        
        Returns:
            解析结果
        """
        page_texts = []
        full_text = []

        # 将 bytes 包装成 BytesIO（模拟文件对象）
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)

            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text() or ""

                    page_texts.append({
                        "page": i + 1,
                        "text": text
                    })

                    full_text.append(text)

                except Exception as e:
                    logger.warning(f"解析第 {i + 1} 页失败: {e}")
                    page_texts.append({
                        "page": i + 1,
                        "text": ""
                    })

        return {
            "text": "\n\n".join(full_text),
            "total_pages": total_pages,
            "page_texts": page_texts,
            "parser": "pdfplumber"
        }

    async def _parse_bytes_with_pypdf2(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        使用 PyPDF2 解析字节流
        
        工作流程：
            1. 将 bytes 包装成 BytesIO 对象
            2. 创建 PdfReader 对象
            3. 提取文本（同 _parse_with_pypdf2）
        
        Args:
            pdf_bytes: PDF 字节流
        
        Returns:
            解析结果
        """
        page_texts = []
        full_text = []

        # 将 bytes 包装成 BytesIO
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)

        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""

                page_texts.append({
                    "page": i + 1,
                    "text": text
                })

                full_text.append(text)

            except Exception as e:
                logger.warning(f"解析第 {i + 1} 页失败: {e}")
                page_texts.append({
                    "page": i + 1,
                    "text": ""
                })

        return {
            "text": "\n\n".join(full_text),
            "total_pages": total_pages,
            "page_texts": page_texts,
            "parser": "PyPDF2"
        }

    # 🔧 修复位置 3：保存分块到数据库
    async def _save_chunks_to_db(
            self,
            pdf_id: str,
            chunks: List[Dict[str, Any]],
            embeddings: List[List[float]]
    ):
        """
        保存分块到数据库
        
        功能说明：
            将文本分块和对应的向量保存到 document_chunks 表
            这是 RAG 系统的核心数据存储
        
        工作流程：
            1. 验证分块数量和向量数量一致
            2. 遍历每个分块
            3. 生成 UUID（分块 ID）
            4. 转换向量格式（List → String）
            5. 转换 metadata 格式（Dict → JSON String）
            6. 插入数据库
        
        数据库表结构（document_chunks）：
            - id: UUID（主键）
            - pdf_id: PDF ID（外键）
            - chunk_index: 分块索引（0, 1, 2, ...）
            - content: 文本内容
            - page_number: 页码
            - token_count: Token 数量
            - embedding: 向量（pgvector 类型）
            - metadata: 元数据（JSONB 类型）
            - created_at: 创建时间
        
        Args:
            pdf_id: PDF ID（外键）
            chunks: 分块列表，格式：
                   [
                       {
                           "chunk_index": 0,
                           "content": "文本内容...",
                           "char_count": 500,
                           "metadata": {
                               "page_number": 1,
                               "start_char": 0,
                               "end_char": 500
                           }
                       },
                       ...
                   ]
            
            embeddings: 向量列表，格式：
                       [
                           [0.1, 0.2, 0.3, ...],  # 1536 维向量
                           [0.4, 0.5, 0.6, ...],
                           ...
                       ]
        
        Raises:
            ValueError: 分块数量和向量数量不匹配
            Exception: 数据库插入失败
        
        示例：
            await _save_chunks_to_db(
                pdf_id="123e4567-e89b-12d3-a456-426614174000",
                chunks=[{"content": "...", "chunk_index": 0, ...}],
                embeddings=[[0.1, 0.2, ...]]
            )
        """
        # 验证分块数量和向量数量一致
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"分块数量({len(chunks)})与向量数量({len(embeddings)})不匹配"
            )

        logger.info(f"开始保存 {len(chunks)} 个分块到数据库")

        # 🔧 修复：在 SQL 中添加 id 字段
        # 准备 SQL 插入语句
        insert_sql = """
            INSERT INTO document_chunks (
                id,                 -- ✅ 分块 ID（UUID）
                pdf_id,             -- PDF ID（外键）
                chunk_index,        -- 分块索引
                content,            -- 文本内容
                page_number,        -- 页码
                token_count,        -- Token 数量
                embedding,          -- 向量（pgvector 类型）
                metadata,           -- 元数据（JSONB 类型）
                created_at          -- 创建时间
            ) VALUES (
                :id,                -- 命名参数
                :pdf_id, 
                :chunk_index, 
                :content, 
                :page_number,
                :token_count, 
                CAST(:embedding AS vector),    -- 转换为 vector 类型
                CAST(:metadata AS jsonb),      -- 转换为 jsonb 类型
                NOW()
            )
        """

        # 遍历每个分块，插入数据库
        for chunk, embedding in zip(chunks, embeddings):
            try:
                # ✅ 生成 UUID（分块 ID）
                chunk_id = str(uuid.uuid4())

                # 将向量转换为字符串格式（pgvector 要求）
                # 格式：[0.1,0.2,0.3,...]
                vector_str = f"[{','.join(map(str, embedding))}]"

                # 将 metadata 转换为 JSON 字符串（JSONB 要求）
                # ensure_ascii=False：保留中文字符
                metadata_str = json.dumps(chunk['metadata'], ensure_ascii=False)

                # 执行插入
                await self.db.execute(
                    insert_sql,
                    id=chunk_id,  # ✅ 现在 SQL 中有 :id 了
                    pdf_id=pdf_id,
                    chunk_index=chunk['chunk_index'],
                    content=chunk['content'],
                    page_number=chunk['metadata'].get('page_number'),
                    token_count=chunk['char_count'],
                    embedding=vector_str,
                    metadata=metadata_str
                )

            except Exception as e:
                # 如果插入失败，记录错误并抛出异常
                logger.error(f"保存分块 {chunk['chunk_index']} 失败: {e}")
                logger.exception(e)  # 打印详细堆栈
                raise

        logger.info(f"数据库保存完成: {len(chunks)} 个分块")


    # 🔧 修复位置 4：删除 PDF 分块
    async def delete_pdf_chunks(self, pdf_id: str):
        """
        删除 PDF 的所有分块
        
        功能说明：
            删除指定 PDF 的所有文档分块（用于重新处理或删除 PDF）
        
        工作流程：
            1. 执行 DELETE 语句
            2. 删除所有 pdf_id 匹配的分块
            3. 记录删除结果
        
        Args:
            pdf_id: PDF ID
        
        示例：
            await delete_pdf_chunks("123e4567-e89b-12d3-a456-426614174000")
        """
        logger.info(f"删除 PDF 分块: {pdf_id}")

        # ✅ 使用命名参数
        result = await self.db.execute(
            "DELETE FROM document_chunks WHERE pdf_id = :pdf_id",
            pdf_id=pdf_id
        )

        logger.info(f"删除完成: {result}")

    # 🔧 修复位置 5：重新处理 PDF
    async def reprocess_pdf(self, pdf_id: str, file_path: str):
        """
        重新处理 PDF
        
        功能说明：
            删除旧的分块和向量，重新处理 PDF
            适用于：
            - 处理失败后重试
            - 更新分块策略后重新处理
            - 更新向量模型后重新处理
        
        工作流程：
            1. 删除旧分块（调用 delete_pdf_chunks）
            2. 更新 PDF 状态为 'processing'
            3. 重新处理 PDF（调用 process_pdf）
        
        Args:
            pdf_id: PDF ID
            file_path: PDF 文件路径
        
        Returns:
            处理结果（同 process_pdf）
        
        示例：
            result = await reprocess_pdf(
                pdf_id="123e4567-e89b-12d3-a456-426614174000",
                file_path="/uploads/document.pdf"
            )
        """
        logger.info(f"重新处理 PDF: {pdf_id}")

        # 删除旧分块
        await self.delete_pdf_chunks(pdf_id)

        # ✅ 使用命名参数 + 正确的字段名
        # 更新 PDF 状态为 'processing'
        await self.db.execute(
            """
            UPDATE pdfs
            SET status = :status,
                "errorMessage" = NULL,
                "updatedAt" = NOW()
            WHERE id = :pdf_id
            """,
            status='processing',
            pdf_id=pdf_id
        )

        # 重新处理
        return await self.process_pdf(file_path, pdf_id)


# ============================================================================
# 全局服务实例（单例模式）
# ============================================================================

_pdf_processor: Optional[PDFProcessor] = None  # 全局实例（初始为 None）


def get_pdf_processor() -> PDFProcessor:
    """
    获取 PDF 处理器实例（单例模式）
    
    单例模式说明：
        - 全局只创建一个 PDFProcessor 实例
        - 避免重复初始化（节省资源）
        - 所有地方共享同一个配置
    
    工作流程：
        1. 检查全局实例是否已创建
        2. 如果未创建，创建新实例
        3. 返回实例
    
    Returns:
        PDFProcessor 实例
    
    示例：
        processor = get_pdf_processor()
        result = await processor.process_pdf(
            file_path="/uploads/document.pdf",
            pdf_id="123e4567-e89b-12d3-a456-426614174000"
        )
    """
    global _pdf_processor  # 声明使用全局变量

    # 如果实例未创建，创建新实例
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()

    return _pdf_processor
