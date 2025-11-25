"""
============================================================================
文档管理 API 路由（完全修复版 - 基于实际表结构）
============================================================================

文件位置：
  rag-service/app/api/v1/documents.py

文件作用：
  提供文档管理相关的 API 接口

主要功能：
  1. 文档列表 - 获取所有文档或指定用户的文档
  2. 文档详情 - 获取单个文档的详细信息
  3. 文档分块 - 获取文档的分块内容（分页）
  4. 调试接口 - 查看数据库表信息

数据库表结构：
  - pdfs 表：存储 PDF 文档元数据
    字段：id, userId, name, fileName, filePath, size, status, 
          totalPages, totalChunks, createdAt, updatedAt, 
          errorMessage, processedAt
  
  - document_chunks 表：存储文档分块
    字段：id, pdf_id, chunk_index, content, page_number, 
          token_count, metadata, createdAt, embedding

技术栈：
  - FastAPI（Web 框架）
  - PostgreSQL（关系型数据库）
  - asyncpg（异步数据库驱动）

API 端点：
  - GET /api/v1/documents/list - 文档列表
  - GET /api/v1/documents/{pdf_id} - 文档详情
  - GET /api/v1/documents/{pdf_id}/chunks - 文档分块
  - GET /api/v1/documents/debug/tables - 调试接口

依赖文件：
  - app/core/database.py（数据库连接）

============================================================================
"""
from fastapi import APIRouter, HTTPException, status, Query  # FastAPI 路由和工具
from typing import Optional  # 类型注解
from loguru import logger  # 日志记录器

from app.core.database import get_database  # 数据库连接

# 创建路由器
router = APIRouter()


# ============================================================================
# 文档列表接口
# ============================================================================

@router.get("/list")
async def list_documents(user_id: Optional[str] = Query(None, description="用户 ID")):
    """
    获取文档列表
    
    功能说明：
      - 获取所有文档或指定用户的文档
      - 按创建时间倒序排列
      - 返回文档基本信息（不包含分块）
    
    Args:
        user_id: 用户 ID（可选）
            - 如果提供，只返回该用户的文档
            - 如果不提供，返回所有文档
    
    Returns:
        文档列表响应：
        {
            "success": true,
            "data": [
                {
                    "id": "uuid",
                    "user_id": "user123",
                    "name": "文档名称",
                    "file_name": "document.pdf",
                    "file_path": "/uploads/xxx.pdf",
                    "size": 1024000,
                    "status": "ready",
                    "total_pages": 10,
                    "total_chunks": 50,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00"
                }
            ],
            "total": 1
        }
    
    状态说明：
      - processing: 正在处理（解析、分块、向量化）
      - ready: 处理完成，可以使用
      - failed: 处理失败
      - unknown: 状态未知
    
    使用示例：
        # 获取所有文档
        GET /api/v1/documents/list
        
        # 获取指定用户的文档
        GET /api/v1/documents/list?user_id=user123
    
    Raises:
        HTTPException 500: 数据库查询失败
    """
    try:
        db = get_database()  # 获取数据库连接

        # ========== 1. 构建 SQL 查询 ==========
        # 使用实际的字段名（驼峰命名）
        # 注意：PostgreSQL 中大小写敏感字段需要加引号
        sql = """
            SELECT 
                id,                 -- 文档 ID
                "userId",           -- 用户 ID（驼峰命名，需要引号）
                name,               -- 文档名称
                "fileName",         -- 文件名（驼峰命名，需要引号）
                "filePath",         -- 文件路径（驼峰命名，需要引号）
                size,               -- 文件大小（字节）
                status,             -- 处理状态
                "totalPages",       -- 总页数（驼峰命名，需要引号）
                "totalChunks",      -- 总分块数（驼峰命名，需要引号）
                "createdAt",        -- 创建时间（驼峰命名，需要引号）
                "updatedAt"         -- 更新时间（驼峰命名，需要引号）
            FROM pdfs
        """

        # ========== 2. 根据参数执行查询 ==========
        if user_id:
            # 查询指定用户的文档
            sql += ' WHERE "userId" = :user_id'  # 添加用户过滤条件
            sql += ' ORDER BY "createdAt" DESC'  # 按创建时间倒序
            rows = await db.fetch(sql, user_id=user_id)  # 执行参数化查询
        else:
            # 查询所有文档
            sql += ' ORDER BY "createdAt" DESC'  # 按创建时间倒序
            rows = await db.fetch(sql)  # 执行查询

        # ========== 3. 映射到 API 响应格式 ==========
        #  映射到 API 响应格式（下划线命名）
        # 说明：
        #   - 数据库使用驼峰命名（userId, fileName）
        #   - API 响应使用下划线命名（user_id, file_name）
        #   - 需要手动映射字段名
        documents = []
        for row in rows:
            try:
                documents.append({
                    "id": row["id"],  # 文档 ID
                    "user_id": row.get("userId"),  # 用户 ID
                    "name": row.get("name") or row.get("fileName", ""),  # 优先使用 name，fallback 到 fileName
                    "file_name": row.get("fileName", ""),  # 文件名
                    "file_path": row.get("filePath", ""),  # 文件路径
                    "size": row.get("size", 0),  # 文件大小
                    "status": row.get("status", "unknown"),  # 处理状态
                    "total_pages": row.get("totalPages", 0),  # 总页数
                    "total_chunks": row.get("totalChunks", 0),  # 总分块数
                    "created_at": row["createdAt"].isoformat() if row.get("createdAt") else None,  # 创建时间（ISO 格式）
                    "updated_at": row["updatedAt"].isoformat() if row.get("updatedAt") else None,  # 更新时间（ISO 格式）
                })
            except Exception as e:
                # 处理单条记录失败时跳过，不影响其他记录
                logger.warning(f"处理文档记录失败: {e}, row: {dict(row)}")
                continue

        logger.info(f"获取文档列表成功: {len(documents)} 个文档")

        # ========== 4. 返回响应 ==========
        return {
            "success": True,  # 操作成功
            "data": documents,  # 文档列表
            "total": len(documents),  # 总数
        }

    except Exception as e:
        # ========== 5. 异常处理 ==========
        logger.error(f"获取文档列表失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败: {str(e)}"
        )


# ============================================================================
# 文档详情接口
# ============================================================================

@router.get("/{pdf_id}")
async def get_document(pdf_id: str):
    """
    获取文档详情
    
    功能说明：
      - 获取单个文档的详细信息
      - 包含错误信息和处理时间
    
    Args:
        pdf_id: 文档 ID（路径参数）
    
    Returns:
        文档详情响应：
        {
            "success": true,
            "data": {
                "id": "uuid",
                "user_id": "user123",
                "name": "文档名称",
                "file_name": "document.pdf",
                "file_path": "/uploads/xxx.pdf",
                "size": 1024000,
                "status": "ready",
                "total_pages": 10,
                "total_chunks": 50,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "error_message": null,
                "processed_at": "2024-01-01T00:00:00"
            }
        }
    
    使用示例：
        GET /api/v1/documents/123e4567-e89b-12d3-a456-426614174000
    
    Raises:
        HTTPException 404: 文档不存在
        HTTPException 500: 数据库查询失败
    """
    try:
        db = get_database()  # 获取数据库连接

        # ========== 1. 查询文档详情 ==========
        #  使用实际的字段名
        row = await db.fetchrow(
            """
            SELECT 
                id,                 -- 文档 ID
                "userId",           -- 用户 ID
                name,               -- 文档名称
                "fileName",         -- 文件名
                "filePath",         -- 文件路径
                size,               -- 文件大小
                status,             -- 处理状态
                "totalPages",       -- 总页数
                "totalChunks",      -- 总分块数
                "createdAt",        -- 创建时间
                "updatedAt",        -- 更新时间
                "errorMessage",     -- 错误信息（处理失败时）
                "processedAt"       -- 处理完成时间
            FROM pdfs
            WHERE id = :pdf_id
            """,
            pdf_id=pdf_id
        )

        # ========== 2. 检查文档是否存在 ==========
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )

        # ========== 3. 返回响应 ==========
        return {
            "success": True,  # 操作成功
            "data": {
                "id": row["id"],  # 文档 ID
                "user_id": row.get("userId"),  # 用户 ID
                "name": row.get("name") or row.get("fileName", ""),  # 文档名称
                "file_name": row.get("fileName", ""),  # 文件名
                "file_path": row.get("filePath", ""),  # 文件路径
                "size": row.get("size", 0),  # 文件大小
                "status": row.get("status", "unknown"),  # 处理状态
                "total_pages": row.get("totalPages", 0),  # 总页数
                "total_chunks": row.get("totalChunks", 0),  # 总分块数
                "created_at": row["createdAt"].isoformat() if row.get("createdAt") else None,  # 创建时间
                "updated_at": row["updatedAt"].isoformat() if row.get("updatedAt") else None,  # 更新时间
                "error_message": row.get("errorMessage"),  # 错误信息（处理失败时）
                "processed_at": row["processedAt"].isoformat() if row.get("processedAt") else None,  # 处理完成时间
            }
        }

    except HTTPException:
        # HTTPException 直接抛出
        raise
    except Exception as e:
        # 其他异常
        logger.error(f"获取文档详情失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档详情失败: {str(e)}"
        )


# ============================================================================
# 文档分块接口
# ============================================================================

@router.get("/{pdf_id}/chunks")
async def get_document_chunks(
    pdf_id: str,  # 文档 ID（路径参数）
    page: int = Query(1, ge=1, description="页码"),  # 页码（从 1 开始）
    page_size: int = Query(20, ge=1, le=100, description="每页数量")  # 每页数量（1-100）
):
    """
    获取文档分块
    
    功能说明：
      - 获取文档的分块内容
      - 支持分页（避免一次返回过多数据）
      - 按分块索引排序
    
    Args:
        pdf_id: 文档 ID（路径参数）
        page: 页码（默认 1，最小 1）
        page_size: 每页数量（默认 20，范围 1-100）
    
    Returns:
        分块列表响应：
        {
            "success": true,
            "data": [
                {
                    "id": "uuid",
                    "chunk_index": 0,
                    "content": "文本内容...",
                    "page_number": 1,
                    "token_count": 100,
                    "metadata": {},
                    "created_at": "2024-01-01T00:00:00"
                }
            ],
            "total": 50,
            "page": 1,
            "page_size": 20,
            "total_pages": 3
        }
    
    分块说明：
      - chunk_index: 分块索引（从 0 开始）
      - content: 文本内容
      - page_number: 所在页码
      - token_count: Token 数量
      - metadata: 元数据（JSON 格式）
    
    使用示例：
        # 获取第 1 页（每页 20 条）
        GET /api/v1/documents/{pdf_id}/chunks?page=1&page_size=20
        
        # 获取第 2 页（每页 50 条）
        GET /api/v1/documents/{pdf_id}/chunks?page=2&page_size=50
    
    Raises:
        HTTPException 404: 文档不存在
        HTTPException 500: 数据库查询失败
    """
    try:
        db = get_database()  # 获取数据库连接

        # ========== 1. 验证 PDF 存在 ==========
        pdf_exists = await db.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pdfs WHERE id = :pdf_id)",
            pdf_id=pdf_id
        )
        # 说明：
        #   - EXISTS 返回布尔值（True/False）
        #   - 比 COUNT(*) 更高效（找到第一条就返回）

        if not pdf_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )

        # ========== 2. 计算偏移量 ==========
        offset = (page - 1) * page_size
        # 说明：
        #   - 第 1 页：offset = 0
        #   - 第 2 页：offset = 20
        #   - 第 3 页：offset = 40

        # ========== 3. 查询总数 ==========
        total = await db.fetchval(
            "SELECT COUNT(*) FROM document_chunks WHERE pdf_id = :pdf_id",
            pdf_id=pdf_id
        )

        # ========== 4. 处理空结果 ==========
        if total == 0:
            return {
                "success": True,
                "data": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
            }

        # ========== 5. 查询分块 ==========
        rows = await db.fetch(
            """
            SELECT 
                id,                 -- 分块 ID
                chunk_index,        -- 分块索引
                content,            -- 文本内容
                page_number,        -- 所在页码
                token_count,        -- Token 数量
                metadata,           -- 元数据（JSON）
                "createdAt"         -- 创建时间
            FROM document_chunks
            WHERE pdf_id = :pdf_id
            ORDER BY chunk_index    -- 按索引排序
            LIMIT :limit OFFSET :offset
            """,
            pdf_id=pdf_id,
            limit=page_size,  # 限制返回数量
            offset=offset  # 偏移量
        )

        # ========== 6. 映射到 API 响应格式 ==========
        chunks = []
        for row in rows:
            try:
                chunks.append({
                    "id": row["id"],  # 分块 ID
                    "chunk_index": row.get("chunk_index", 0),  # 分块索引
                    "content": row.get("content", ""),  # 文本内容
                    "page_number": row.get("page_number"),  # 所在页码
                    "token_count": row.get("token_count", 0),  # Token 数量
                    "metadata": row.get("metadata", {}),  # 元数据
                    "created_at": row["createdAt"].isoformat() if row.get("createdAt") else None,  # 创建时间
                })
            except Exception as e:
                # 处理单条记录失败时跳过
                logger.warning(f"处理分块记录失败: {e}")
                continue

        # ========== 7. 计算总页数 ==========
        total_pages = (total + page_size - 1) // page_size
        # 说明：
        #   - 向上取整（例如：total=50, page_size=20 → total_pages=3）
        #   - 公式：(total + page_size - 1) // page_size

        # ========== 8. 返回响应 ==========
        return {
            "success": True,  # 操作成功
            "data": chunks,  # 分块列表
            "total": total,  # 总数
            "page": page,  # 当前页码
            "page_size": page_size,  # 每页数量
            "total_pages": total_pages,  # 总页数
        }

    except HTTPException:
        # HTTPException 直接抛出
        raise
    except Exception as e:
        # 其他异常
        logger.error(f"获取文档分块失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档分块失败: {str(e)}"
        )


# ============================================================================
# 调试接口
# ============================================================================

@router.get("/debug/tables")
async def debug_tables():
    """
    调试：查看数据库表信息
    
    功能说明：
      - 查看数据库表的记录数
      - 查看表结构（字段名和类型）
      - 用于开发调试
    
    Returns:
        调试信息：
        {
            "success": true,
            "tables": {
                "pdfs": {
                    "count": 10,
                    "columns": [
                        {"name": "id", "type": "uuid"},
                        {"name": "userId", "type": "text"},
                        ...
                    ]
                },
                "document_chunks": {
                    "count": 500
                }
            }
        }
    
    使用示例：
        GET /api/v1/documents/debug/tables
    
    注意：
      - 仅用于开发调试
      - 生产环境应禁用此接口
    """
    try:
        db = get_database()  # 获取数据库连接

        # ========== 1. 检查 pdfs 表 ==========
        pdfs_count = await db.fetchval("SELECT COUNT(*) FROM pdfs")

        # ========== 2. 检查 document_chunks 表 ==========
        chunks_count = await db.fetchval("SELECT COUNT(*) FROM document_chunks")

        # ========== 3. 获取表结构 ==========
        # 查询 information_schema.columns 获取表结构
        pdfs_columns = await db.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'pdfs'
            ORDER BY ordinal_position
        """)
        # 说明：
        #   - information_schema.columns: PostgreSQL 系统表，存储所有表的字段信息
        #   - column_name: 字段名
        #   - data_type: 数据类型
        #   - ordinal_position: 字段顺序

        # ========== 4. 返回响应 ==========
        return {
            "success": True,  # 操作成功
            "tables": {
                "pdfs": {
                    "count": pdfs_count,  # 记录数
                    "columns": [  # 字段列表
                        {
                            "name": row["column_name"],  # 字段名
                            "type": row["data_type"]  # 数据类型
                        }
                        for row in pdfs_columns
                    ]
                },
                "document_chunks": {
                    "count": chunks_count  # 记录数
                }
            }
        }

    except Exception as e:
        # ========== 5. 异常处理 ==========
        logger.error(f"调试失败: {e}")
        logger.exception(e)  # 输出完整堆栈
        return {
            "success": False,  # 操作失败
            "error": str(e)  # 错误信息
        }


# ============================================================================
# 数据库字段映射说明
# ============================================================================
# PostgreSQL 表字段（驼峰命名）→ API 响应字段（下划线命名）
#
# pdfs 表：
#   - userId → user_id
#   - fileName → file_name
#   - filePath → file_path
#   - totalPages → total_pages
#   - totalChunks → total_chunks
#   - createdAt → created_at
#   - updatedAt → updated_at
#   - errorMessage → error_message
#   - processedAt → processed_at
#
# document_chunks 表：
#   - chunk_index → chunk_index
#   - page_number → page_number
#   - token_count → token_count
#   - createdAt → created_at

# ============================================================================
# 分页计算说明
# ============================================================================
# 分页参数：
#   - page: 页码（从 1 开始）
#   - page_size: 每页数量
#
# 计算公式：
#   - offset = (page - 1) * page_size
#   - total_pages = (total + page_size - 1) // page_size
#
# 示例：
#   total = 50, page_size = 20
#   - 第 1 页：offset = 0, limit = 20 → 记录 1-20
#   - 第 2 页：offset = 20, limit = 20 → 记录 21-40
#   - 第 3 页：offset = 40, limit = 20 → 记录 41-50
#   - total_pages = (50 + 20 - 1) // 20 = 3

# ============================================================================
# SQL 注入防护
# ============================================================================
# 使用参数化查询防止 SQL 注入：
#    错误：f"SELECT * FROM pdfs WHERE id = '{pdf_id}'"
#    正确："SELECT * FROM pdfs WHERE id = :pdf_id", pdf_id=pdf_id
#
# 说明：
#   - 参数化查询会自动转义特殊字符
#   - 防止恶意 SQL 注入攻击

# ============================================================================
# 性能优化建议
# ============================================================================
# 1. 索引优化
#    - 在 pdf_id 字段上创建索引
#    - 在 userId 字段上创建索引
#    - 在 createdAt 字段上创建索引
#
# 2. 分页优化
#    - 使用 LIMIT/OFFSET 分页
#    - 避免一次查询过多数据
#
# 3. 查询优化
#    - 只查询需要的字段
#    - 使用 EXISTS 代替 COUNT(*)
#
# 4. 缓存优化
#    - 缓存文档列表（Redis）
#    - 缓存文档详情（Redis）
