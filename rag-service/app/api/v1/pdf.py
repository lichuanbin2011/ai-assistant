"""
============================================================================
PDF 处理 API 路由（完全修复版）
============================================================================

文件位置：
  rag-service/app/api/v1/pdf.py

文件作用：
  提供 PDF 文档上传、处理、删除等管理接口

主要功能：
  1. PDF 上传 - 上传 PDF 文件并自动处理
  2. PDF 重新处理 - 重新解析和向量化
  3. PDF 删除 - 删除文档及其分块
  4. 状态查询 - 查询处理状态

PDF 处理流程：
  上传文件 → 保存文件 → 创建数据库记录 → 解析 PDF 
  → 文本分块 → 向量化 → 存储向量 → 更新状态

技术栈：
  - FastAPI（Web 框架）
  - PyPDF2（PDF 解析）
  - Sentence Transformers（向量化）
  - PostgreSQL + pgvector（向量存储）

API 端点：
  - POST /api/v1/pdf/upload - 上传 PDF
  - POST /api/v1/pdf/{pdf_id}/reprocess - 重新处理
  - DELETE /api/v1/pdf/{pdf_id} - 删除 PDF
  - GET /api/v1/pdf/{pdf_id}/status - 查询状态

依赖文件：
  - app/services/pdf_processor.py（PDF 处理服务）
  - app/core/database.py（数据库连接）
  - app/core/config.py（配置管理）

============================================================================
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form  # FastAPI 路由和工具
from typing import Optional  # 类型注解
from loguru import logger  # 日志记录器
import os  # 文件操作
import uuid  # UUID 生成
from pathlib import Path  # 路径操作

from app.services.pdf_processor import get_pdf_processor  # PDF 处理服务
from app.core.database import get_database  # 数据库连接
from app.core.config import get_settings  # 配置管理

# 创建路由器
router = APIRouter()
settings = get_settings()  # 获取配置


# ============================================================================
# PDF 上传接口
# ============================================================================

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),  # 上传的文件（必填）
    user_id: Optional[str] = Form(None)  # 用户 ID（可选）
):
    """
    上传并处理 PDF 文件
    
    功能说明：
      - 上传 PDF 文件到服务器
      - 验证文件类型和大小
      - 保存文件到本地
      - 创建数据库记录
      - 异步处理 PDF（解析、分块、向量化）
    
    处理流程：
      1. 验证文件类型（必须是 .pdf）
      2. 验证文件大小（最大 20MB）
      3. 保存文件到 uploads 目录
      4. 创建数据库记录（状态：processing）
      5. 解析 PDF（提取文本）
      6. 文本分块（按页或按大小）
      7. 向量化（转换为向量）
      8. 存储向量到数据库
      9. 更新状态（ready 或 failed）

    Args:
        file: PDF 文件（multipart/form-data）
        user_id: 用户 ID（可选，用于多租户场景）

    Returns:
        处理结果：
        {
            "success": true,
            "data": {
                "id": "uuid",
                "name": "document.pdf",
                "fileName": "uuid.pdf",
                "filePath": "uploads/uuid.pdf",
                "size": 1024000,
                "status": "ready",
                "totalPages": 10,
                "totalChunks": 50
            },
            "message": "PDF 上传并处理成功"
        }
    
    状态说明：
      - processing: 正在处理
      - ready: 处理完成
      - failed: 处理失败
    
    使用示例：
        ```bash
        curl -X POST http://localhost:8001/api/v1/pdf/upload \
          -F "file=@document.pdf" \
          -F "user_id=user123"
        ```
    
    Raises:
        HTTPException 400: 文件类型错误或文件过大
        HTTPException 500: 上传或处理失败
    """
    try:
        logger.info(f"收到 PDF 上传请求: {file.filename}")

        # ====================================================================
        # 1. 验证文件类型
        # ====================================================================
        # 说明：
        #   - 只允许上传 .pdf 文件
        #   - 使用 lower() 忽略大小写（.PDF、.Pdf 也可以）
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 PDF 文件上传"
            )

        # ====================================================================
        # 2. 读取文件内容
        # ====================================================================
        content = await file.read()  # 读取文件内容（bytes）
        file_size = len(content)  # 文件大小（字节）

        # 验证文件大小（最大 20MB）
        max_size = 20 * 1024 * 1024  # 20MB = 20 * 1024 * 1024 bytes
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件大小不能超过 {max_size / 1024 / 1024:.0f}MB"
            )

        logger.info(f"文件大小: {file_size / 1024 / 1024:.2f}MB")

        # ====================================================================
        # 3. 保存文件
        # ====================================================================
        # 创建上传目录
        upload_dir = Path("uploads")  # uploads 目录
        upload_dir.mkdir(exist_ok=True)  # 如果不存在则创建

        # 生成唯一文件名
        file_id = str(uuid.uuid4())  # 生成 UUID（例如：123e4567-e89b-12d3-a456-426614174000）
        saved_file_name = f"{file_id}.pdf"  # 保存的文件名（例如：123e4567-e89b-12d3-a456-426614174000.pdf）
        file_path = upload_dir / saved_file_name  # 完整路径（例如：uploads/123e4567-e89b-12d3-a456-426614174000.pdf）

        # 保存文件到磁盘
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"文件保存成功: {file_path}")

        # ====================================================================
        # 4. 创建数据库记录
        # ====================================================================
        db = get_database()  # 获取数据库连接

        pdf_id = str(uuid.uuid4())  # 生成 PDF ID

        # 修复 1：使用命名参数（:param_name）
        # 修复 2：添加所有必填字段，包括 fileName
        # 修复 3：字段名使用双引号（驼峰命名）
        await db.execute(
            """
            INSERT INTO pdfs (
                id,                 -- PDF ID
                "userId",           -- 用户 ID（驼峰命名，需要引号）
                name,               -- 文档名称（原始文件名，用于显示）
                "fileName",         -- 文件名（保存的文件名，uuid.pdf）
                "filePath",         -- 文件路径（完整路径）
                size,               -- 文件大小（字节）
                status,             -- 处理状态（processing/ready/failed）
                "createdAt",        -- 创建时间
                "updatedAt"         -- 更新时间
            ) VALUES (
                :pdf_id,            -- PDF ID
                :user_id,           -- 用户 ID
                :name,              -- 原始文件名
                :file_name,         -- 保存的文件名
                :file_path,         -- 完整路径
                :size,              -- 文件大小
                :status,            -- 状态：processing
                NOW(),              -- 当前时间
                NOW()               -- 当前时间
            )
            """,
            pdf_id=pdf_id,
            user_id=user_id,
            name=file.filename,              # 原始文件名（用于显示）
            file_name=saved_file_name,       # 保存的文件名（uuid.pdf）
            file_path=str(file_path),        # 完整路径
            size=file_size,
            status="processing"              # 初始状态：processing
        )
        # 说明：
        #   - name: 原始文件名（例如：document.pdf），用于前端显示
        #   - fileName: 保存的文件名（例如：123e4567.pdf），用于后端存储
        #   - filePath: 完整路径（例如：uploads/123e4567.pdf），用于文件操作

        logger.info(f"数据库记录创建成功: {pdf_id}")

        # ====================================================================
        # 5. 异步处理 PDF（后台任务）
        # ====================================================================
        pdf_processor = get_pdf_processor()  # 获取 PDF 处理服务

        try:
            # 执行 PDF 处理
            result = await pdf_processor.process_pdf(
                file_path=str(file_path),  # 文件路径
                pdf_id=pdf_id  # PDF ID
            )
            # 说明：
            #   - process_pdf 会执行：
            #     1. 解析 PDF（提取文本）
            #     2. 文本分块（按页或按大小）
            #     3. 向量化（转换为向量）
            #     4. 存储向量到数据库
            #     5. 更新 PDF 状态为 ready
            #   - 返回：
            #     {
            #       "total_pages": 10,
            #       "total_chunks": 50
            #     }

            logger.info(f"PDF 处理成功: {pdf_id}")

            # ========== 返回成功响应 ==========
            return {
                "success": True,  # 操作成功
                "data": {
                    "id": pdf_id,  # PDF ID
                    "name": file.filename,  # 原始文件名
                    "fileName": saved_file_name,  # 保存的文件名
                    "filePath": str(file_path),  # 完整路径
                    "size": file_size,  # 文件大小
                    "status": "ready",  # 状态：ready
                    "totalPages": result["total_pages"],  # 总页数
                    "totalChunks": result["total_chunks"],  # 总分块数
                },
                "message": "PDF 上传并处理成功"
            }

        except Exception as process_error:
            # ========== 处理失败 ==========
            logger.error(f"PDF 处理失败: {process_error}")
            logger.exception(process_error)  # 输出完整堆栈

            # 更新状态为失败
            await db.execute(
                """
                UPDATE pdfs
                SET status = :status,
                    "errorMessage" = :error_message,
                    "updatedAt" = NOW()
                WHERE id = :pdf_id
                """,
                status="failed",
                error_message=str(process_error),
                pdf_id=pdf_id
            )

            # ========== 返回失败响应 ==========
            return {
                "success": False,  # 操作失败
                "data": {
                    "id": pdf_id,  # PDF ID
                    "name": file.filename,  # 原始文件名
                    "fileName": saved_file_name,  # 保存的文件名
                    "filePath": str(file_path),  # 完整路径
                    "size": file_size,  # 文件大小
                    "status": "failed",  # 状态：failed
                },
                "error": str(process_error),  # 错误信息
                "message": "PDF 上传成功但处理失败"
            }

    # ====================================================================
    # 异常处理
    # ====================================================================
    except HTTPException:
        # HTTPException 直接抛出
        raise
    except Exception as e:
        # 其他异常
        logger.error(f"上传失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}"
        )


# ============================================================================
# PDF 重新处理接口
# ============================================================================

@router.post("/{pdf_id}/reprocess")
async def reprocess_pdf(pdf_id: str):
    """
    重新处理 PDF
    
    功能说明：
      - 重新解析 PDF 文件
      - 重新分块和向量化
      - 更新数据库记录
    
    使用场景：
      - 处理失败后重试
      - 更新分块策略
      - 更新向量化模型
    
    Args:
        pdf_id: PDF ID（路径参数）
    
    Returns:
        处理结果：
        {
            "success": true,
            "data": {
                "total_pages": 10,
                "total_chunks": 50
            },
            "message": "PDF 重新处理成功"
        }
    
    使用示例：
        POST /api/v1/pdf/123e4567-e89b-12d3-a456-426614174000/reprocess
    
    Raises:
        HTTPException 404: PDF 不存在或文件不存在
        HTTPException 500: 处理失败
    """
    try:
        logger.info(f"重新处理 PDF: {pdf_id}")

        db = get_database()  # 获取数据库连接

        # ========== 1. 查询 PDF 记录 ==========
        # 使用命名参数
        pdf_record = await db.fetchrow(
            """
            SELECT id, "filePath"
            FROM pdfs
            WHERE id = :pdf_id
            """,
            pdf_id=pdf_id
        )

        # ========== 2. 检查 PDF 是否存在 ==========
        if not pdf_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF 不存在"
            )

        file_path = pdf_record["filePath"]  # 文件路径

        # ========== 3. 检查文件是否存在 ==========
        if not Path(file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF 文件不存在"
            )

        # ========== 4. 重新处理 PDF ==========
        pdf_processor = get_pdf_processor()
        result = await pdf_processor.reprocess_pdf(pdf_id, file_path)
        # 说明：
        #   - reprocess_pdf 会：
        #     1. 删除旧的分块和向量
        #     2. 重新解析 PDF
        #     3. 重新分块和向量化
        #     4. 更新数据库记录

        # ========== 5. 返回响应 ==========
        return {
            "success": True,  # 操作成功
            "data": result,  # 处理结果
            "message": "PDF 重新处理成功"
        }

    # ========== 6. 异常处理 ==========
    except HTTPException:
        # HTTPException 直接抛出
        raise
    except Exception as e:
        # 其他异常
        logger.error(f"重新处理失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新处理失败: {str(e)}"
        )


# ============================================================================
# PDF 删除接口
# ============================================================================

@router.delete("/{pdf_id}")
async def delete_pdf(pdf_id: str):
    """
    删除 PDF 及其分块
    
    功能说明：
      - 删除数据库中的 PDF 记录
      - 删除所有分块和向量
      - 删除磁盘上的文件
    
    删除流程：
      1. 查询 PDF 记录
      2. 删除所有分块（document_chunks 表）
      3. 删除 PDF 记录（pdfs 表）
      4. 删除磁盘文件
    
    Args:
        pdf_id: PDF ID（路径参数）
    
    Returns:
        删除结果：
        {
            "success": true,
            "message": "PDF 删除成功"
        }
    
    使用示例：
        DELETE /api/v1/pdf/123e4567-e89b-12d3-a456-426614174000
    
    Raises:
        HTTPException 404: PDF 不存在
        HTTPException 500: 删除失败
    """
    try:
        logger.info(f"删除 PDF: {pdf_id}")

        db = get_database()  # 获取数据库连接
        pdf_processor = get_pdf_processor()  # 获取 PDF 处理服务

        # ========== 1. 查询 PDF 记录 ==========
        # 使用命名参数
        pdf_record = await db.fetchrow(
            """
            SELECT id, "filePath"
            FROM pdfs
            WHERE id = :pdf_id
            """,
            pdf_id=pdf_id
        )

        # ========== 2. 检查 PDF 是否存在 ==========
        if not pdf_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF 不存在"
            )

        file_path = pdf_record["filePath"]  # 文件路径

        # ========== 3. 删除分块 ==========
        await pdf_processor.delete_pdf_chunks(pdf_id)
        # 说明：
        #   - 删除 document_chunks 表中的所有分块
        #   - 包括向量数据

        # ========== 4. 删除 PDF 记录 ==========
        # 使用命名参数
        await db.execute(
            "DELETE FROM pdfs WHERE id = :pdf_id",
            pdf_id=pdf_id
        )

        # ========== 5. 删除文件 ==========
        try:
            if Path(file_path).exists():
                os.remove(file_path)  # 删除文件
                logger.info(f"文件删除成功: {file_path}")
        except Exception as e:
            # 文件删除失败不影响整体流程
            logger.warning(f"文件删除失败: {e}")

        # ========== 6. 返回响应 ==========
        return {
            "success": True,  # 操作成功
            "message": "PDF 删除成功"
        }

    # ========== 7. 异常处理 ==========
    except HTTPException:
        # HTTPException 直接抛出
        raise
    except Exception as e:
        # 其他异常
        logger.error(f"删除失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除失败: {str(e)}"
        )


# ============================================================================
# PDF 状态查询接口
# ============================================================================

@router.get("/{pdf_id}/status")
async def get_pdf_status(pdf_id: str):
    """
    查询 PDF 处理状态
    
    功能说明：
      - 查询 PDF 的处理状态
      - 返回页数、分块数、错误信息等
    
    状态说明：
      - processing: 正在处理
      - ready: 处理完成
      - failed: 处理失败
    
    Args:
        pdf_id: PDF ID（路径参数）
    
    Returns:
        状态信息：
        {
            "success": true,
            "data": {
                "id": "uuid",
                "name": "document.pdf",
                "fileName": "uuid.pdf",
                "status": "ready",
                "totalPages": 10,
                "totalChunks": 50,
                "errorMessage": null
            }
        }
    
    使用示例：
        GET /api/v1/pdf/123e4567-e89b-12d3-a456-426614174000/status
    
    Raises:
        HTTPException 404: PDF 不存在
        HTTPException 500: 查询失败
    """
    try:
        db = get_database()  # 获取数据库连接

        # ========== 1. 查询 PDF 状态 ==========
        # 使用命名参数
        pdf_record = await db.fetchrow(
            """
            SELECT 
                id,                 -- PDF ID
                name,               -- 文档名称
                "fileName",         -- 文件名
                status,             -- 处理状态
                "totalPages",       -- 总页数
                "totalChunks",      -- 总分块数
                "errorMessage"      -- 错误信息
            FROM pdfs
            WHERE id = :pdf_id
            """,
            pdf_id=pdf_id
        )

        # ========== 2. 检查 PDF 是否存在 ==========
        if not pdf_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF 不存在"
            )

        # ========== 3. 返回响应 ==========
        return {
            "success": True,  # 操作成功
            "data": {
                "id": pdf_record["id"],  # PDF ID
                "name": pdf_record.get("name") or pdf_record.get("fileName", ""),  # 文档名称
                "fileName": pdf_record.get("fileName", ""),  # 文件名
                "status": pdf_record["status"],  # 处理状态
                "totalPages": pdf_record.get("totalPages"),  # 总页数
                "totalChunks": pdf_record.get("totalChunks"),  # 总分块数
                "errorMessage": pdf_record.get("errorMessage"),  # 错误信息
            }
        }

    # ========== 4. 异常处理 ==========
    except HTTPException:
        # HTTPException 直接抛出
        raise
    except Exception as e:
        # 其他异常
        logger.error(f"查询状态失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询状态失败: {str(e)}"
        )


# ============================================================================
# PDF 处理流程详解
# ============================================================================
# 1. 文件上传
#    - 验证文件类型（.pdf）
#    - 验证文件大小（最大 20MB）
#    - 保存文件到 uploads 目录
#
# 2. 数据库记录
#    - 创建 pdfs 表记录
#    - 状态：processing
#
# 3. PDF 解析
#    - 使用 PyPDF2 解析 PDF
#    - 提取文本内容
#    - 按页或按大小分块
#
# 4. 文本分块
#    - 分块策略：按页、按大小、按段落
#    - 分块大小：500-1000 字符
#    - 重叠：50-100 字符
#
# 5. 向量化
#    - 使用 Sentence Transformers 模型
#    - 批量向量化（提高效率）
#    - 缓存向量化结果
#
# 6. 存储向量
#    - 存储到 document_chunks 表
#    - 使用 pgvector 扩展
#    - 创建向量索引（加速检索）
#
# 7. 更新状态
#    - 状态：ready 或 failed
#    - 记录总页数和总分块数

# ============================================================================
# 文件命名说明
# ============================================================================
# name vs fileName:
#   - name: 原始文件名（例如：document.pdf）
#     用途：前端显示，用户识别
#   
#   - fileName: 保存的文件名（例如：123e4567.pdf）
#     用途：后端存储，避免文件名冲突
#
# 为什么使用 UUID：
#   - 避免文件名冲突（多个用户上传同名文件）
#   - 防止路径遍历攻击（../../../etc/passwd）
#   - 便于管理和追踪

# ============================================================================
# 错误处理说明
# ============================================================================
# 1. 文件类型错误（400）
#    错误：HTTPException(400, "仅支持 PDF 文件上传")
#    原因：上传的不是 .pdf 文件
#    解决：检查文件扩展名
#
# 2. 文件过大（400）
#    错误：HTTPException(400, "文件大小不能超过 20MB")
#    原因：文件大小超过限制
#    解决：压缩文件或分割文件
#
# 3. PDF 不存在（404）
#    错误：HTTPException(404, "PDF 不存在")
#    原因：数据库中没有该 PDF 记录
#    解决：检查 pdf_id 是否正确
#
# 4. 文件不存在（404）
#    错误：HTTPException(404, "PDF 文件不存在")
#    原因：磁盘上的文件被删除
#    解决：重新上传文件
#
# 5. 处理失败（500）
#    错误：HTTPException(500, "上传失败")
#    原因：解析失败、向量化失败等
#    解决：查看错误日志，检查文件是否损坏

# ============================================================================
# 性能优化建议
# ============================================================================
# 1. 异步处理
#    - 使用后台任务处理 PDF
#    - 避免阻塞主线程
#
# 2. 批量向量化
#    - 批量处理分块
#    - 利用 GPU 并行计算
#
# 3. 缓存
#    - 缓存向量化结果
#    - 避免重复计算
#
# 4. 文件压缩
#    - 压缩上传的文件
#    - 减少存储空间
#
# 5. 清理策略
#    - 定期清理失败的文件
#    - 定期清理过期的文件
