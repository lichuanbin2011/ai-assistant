"""
============================================================================
RAG 聊天 API 路由（完全修复版 - 处理检索结果为空的情况）
============================================================================

文件位置：
  rag-service/app/api/v1/chat.py

文件作用：
  提供 RAG（检索增强生成）聊天接口，支持与 PDF 文档对话

主要功能：
  1. PDF 文档验证 - 检查文档是否存在和可用
  2. 查询重写 - 优化用户问题
  3. 智能检索 - 从文档中检索相关内容
  4. 上下文构建 - 将检索结果格式化为 prompt
  5. LLM 生成 - 调用大模型生成回答
  6. 降级处理 - 检索失败时降级为普通对话

核心流程：
  用户提问 → 查询重写 → 向量检索 → 构建上下文 → LLM 生成 → 返回回答

技术栈：
  - FastAPI（Web 框架）
  - PostgreSQL + pgvector（向量数据库）
  - LLM Service（大模型调用）

API 端点：
  - POST /api/v1/chat/chat - RAG 对话
  - POST /api/v1/chat - 简化版（别名）

依赖文件：
  - app/models/schemas.py（数据模型）
  - app/core/database.py（数据库连接）
  - app/core/rag/query_rewrite.py（查询重写）
  - app/core/rag/retrieval.py（检索逻辑）
  - app/services/llm.py（LLM 服务）

============================================================================
"""
from fastapi import APIRouter, HTTPException, status  # FastAPI 路由和异常
from loguru import logger  # 日志记录器

from app.models.schemas import (
    ChatRequest,  # 聊天请求模型
    ChatResponse,  # 聊天响应模型
    ChatMetadata,  # 聊天元数据模型
    DocumentSource,  # 文档来源模型
    ErrorResponse,  # 错误响应模型
)
from app.core.database import get_database  # 数据库连接
from app.core.rag.query_rewrite import get_query_rewriter  # 查询重写器
from app.core.rag.retrieval import get_retriever  # 检索器
from app.services.llm import get_llm_service  # LLM 服务
from datetime import datetime  # 时间戳

# 创建路由器
router = APIRouter()


# ============================================================================
# RAG 聊天接口
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_pdf(request: ChatRequest):
    """
    与 PDF 文档进行 RAG 对话
    
    功能说明：
      - 验证 PDF 文档是否存在和可用
      - 重写用户查询（优化检索效果）
      - 从文档中检索相关内容
      - 构建 RAG prompt 或降级 prompt
      - 调用 LLM 生成回答
      - 返回回答和来源信息
    
    核心流程：
      1. 验证 PDF 存在 → 2. 检查处理状态 → 3. 查询重写 
      → 4. 智能检索 → 5. 构建上下文 → 6. 调用 LLM → 7. 返回响应
    
    Args:
        request: 聊天请求
            {
                "pdf_id": "uuid",
                "message": "这个文档讲了什么？",
                "model": "openai/gpt-4o-mini"  # 可选
            }

    Returns:
        聊天响应：
        {
            "success": true,
            "response": "AI 生成的回答",
            "metadata": {
                "pdf_name": "文档名称",
                "total_pages": 10,
                "total_chunks": 50,
                "chunks_retrieved": 3,
                "sources": [...],
                "model": "openai/gpt-4o-mini",
                "rag_enabled": true,
                "timestamp": "2024-01-01T00:00:00"
            }
        }
    
    Raises:
        HTTPException 404: PDF 不存在
        HTTPException 400: PDF 处理中/失败/状态异常
        HTTPException 500: 检索失败、LLM 调用失败
    
    使用示例：
        POST /api/v1/chat/chat
        {
            "pdf_id": "123e4567-e89b-12d3-a456-426614174000",
            "message": "这个文档的主要内容是什么？"
        }
    """
    try:
        logger.info(f"收到聊天请求: pdf_id={request.pdf_id}, query_len={len(request.message)}")

        # ========== 初始化服务 ==========
        db = get_database()  # 数据库连接
        query_rewriter = get_query_rewriter()  # 查询重写器
        retriever = get_retriever()  # 检索器
        llm_service = get_llm_service()  # LLM 服务

        # ====================================================================
        # 1. 验证 PDF 存在
        # ====================================================================
        # 查询 PDF 信息
        pdf_record = await db.fetchrow(
            """
            SELECT id, name, "fileName", "filePath", status, "totalPages", "totalChunks"
            FROM pdfs
            WHERE id = :pdf_id
            """,
            pdf_id=request.pdf_id
        )
        # 说明：
        #   - 使用参数化查询防止 SQL 注入
        #   - 查询字段：id, name, fileName, filePath, status, totalPages, totalChunks
        #   - 注意：PostgreSQL 中大小写敏感字段需要加引号（如 "fileName"）

        # 检查 PDF 是否存在
        if not pdf_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF 不存在"
            )

        # 优先使用 name，fallback 到 fileName
        pdf_name = pdf_record.get("name") or pdf_record.get("fileName", "未知文档")
        total_pages = pdf_record.get("totalPages", 0)  # 总页数
        total_chunks = pdf_record.get("totalChunks", 0)  # 总文本块数

        # ====================================================================
        # 2. 检查 PDF 处理状态
        # ====================================================================
        pdf_status = pdf_record["status"]
        # PDF 状态说明：
        #   - processing: 正在处理（解析、分块、向量化）
        #   - ready: 处理完成，可以使用
        #   - failed: 处理失败

        # 检查状态：processing
        if pdf_status == "processing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF 文件正在处理中，请稍后再试"
            )

        # 检查状态：failed
        if pdf_status == "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF 文件处理失败"
            )

        # 检查状态：其他异常状态
        if pdf_status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF 文件状态异常: {pdf_status}"
            )

        # ====================================================================
        # 3. 查询重写
        # ====================================================================
        # 功能说明：
        #   - 优化用户查询，提高检索效果
        #   - 例如："这个文档讲了什么？" → "文档主要内容 核心观点 关键信息"
        rewrite_result = await query_rewriter.rewrite(request.message)
        final_query = rewrite_result["final_query"]  # 重写后的查询

        logger.info(f"查询重写完成: type={rewrite_result['query_type']}")
        logger.debug(f"原始查询: {request.message}")
        logger.debug(f"最终查询: {final_query}")

        # ====================================================================
        # 4. 智能检索（添加异常处理）
        # ====================================================================
        # 功能说明：
        #   - 使用向量相似度检索相关文档块
        #   - 支持多种检索策略（向量检索、关键词检索、混合检索）
        try:
            chunks = await retriever.smart_retrieval(
                query=final_query,  # 重写后的查询
                pdf_id=request.pdf_id,  # PDF ID
                pdf_record=dict(pdf_record)  # PDF 元数据
            )
        except Exception as e:
            logger.error(f"检索失败: {e}")
            logger.exception(e)  # 输出完整堆栈
            # 检索失败时设置为空列表，不抛出异常
            chunks = []

        logger.info(f"检索到 {len(chunks)} 个相关文档块")

        #  修改：移除检索结果为空时的异常，改为降级处理
        # 说明：
        #   - 旧版本：检索结果为空时抛出异常
        #   - 新版本：检索结果为空时降级为普通对话
        # if not chunks:
        #     raise HTTPException(
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #         detail="未找到相关文档内容，请尝试换一种方式提问"
        #     )

        # ====================================================================
        # 5. 构建上下文（处理检索结果为空的情况）
        # ====================================================================
        rag_enabled = len(chunks) > 0  # 是否启用 RAG（有检索结果）

        if rag_enabled:
            # ========== 情况 1：有检索结果，使用 RAG ==========
            context_parts = []
            for i, chunk in enumerate(chunks):
                # 构建页码信息
                page_info = f" (第 {chunk.get('page_number', 'N/A')} 页)" if chunk.get('page_number') else ""
                
                # 构建相似度信息
                similarity = chunk.get('similarity', 0)
                similarity_pct = f"{similarity * 100:.1f}%" if similarity else "N/A"

                # 格式化文档块
                context_parts.append(
                    f"[来源 {i + 1}{page_info} | 相关度: {similarity_pct}]\n{chunk['content']}"
                )

            # 拼接所有文档块
            context = "\n\n---\n\n".join(context_parts)

            # 使用原有的 RAG prompt 构建方法
            messages = llm_service.build_rag_prompt(
                query=request.message,  # 原始查询
                context=context,  # 检索到的上下文
                pdf_name=pdf_name,  # PDF 名称
                total_pages=total_pages,  # 总页数
                total_chunks=total_chunks,  # 总文本块数
                chunks_retrieved=len(chunks),  # 检索到的文本块数
            )
            # 说明：
            #   - build_rag_prompt 会构建包含系统提示词和用户消息的完整 prompt
            #   - 系统提示词会告诉 LLM 如何使用检索到的上下文

        else:
            # ========== 情况 2：无检索结果，降级为普通对话 ==========
            # 无检索结果，降级为普通对话
            logger.warning(f"未找到相关内容，降级为普通对话")

            # 构建降级 prompt
            system_prompt = f"""你是一个专业的文档分析助手。

                            用户正在查询文档《{pdf_name}》（共 {total_pages} 页，{total_chunks} 个文本块），但系统未能检索到与问题直接相关的内容。

                            请礼貌地告知用户：
                            1. 系统未能在文档中找到与问题直接相关的内容
                            2. 建议用户尝试：
                            - 使用不同的关键词重新提问（例如：使用文档中可能出现的专业术语）
                            - 提供更具体的问题描述
                            - 尝试询问文档的整体结构或主要章节
                            - 如果知道具体页码，可以直接询问该页内容
                            3. 如果可能，基于常识和文档类型（从文件名推测）提供一些通用建议

                            注意：
                            - 不要编造文档中不存在的内容
                            - 保持礼貌和专业
                            - 鼓励用户换一种方式提问"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ]
            # 说明：
            #   - 降级 prompt 会告诉 LLM 系统未找到相关内容
            #   - 引导用户换一种方式提问
            #   - 避免 LLM 编造不存在的内容

        # ====================================================================
        # 6. 调用 LLM（添加异常处理）
        # ====================================================================
        logger.info(f"调用 LLM: model={request.model or llm_service.model_main}, rag_enabled={rag_enabled}")

        try:
            ai_response = await llm_service.chat(
                messages=messages,  # 构建的 prompt
                model=request.model,  # 指定模型（可选）
                temperature=0.7,  # 温度参数（0-2，越高越随机）
                max_tokens=2000,  # 最大生成 token 数
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            logger.exception(e)  # 输出完整堆栈
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI 服务暂时不可用: {str(e)}"
            )

        # ====================================================================
        # 7. 构建响应（根据 rag_enabled 调整响应）
        # ====================================================================
        # 构建元数据
        metadata = ChatMetadata(
            pdf_name=pdf_name,  # PDF 名称
            total_pages=total_pages,  # 总页数
            total_chunks=total_chunks,  # 总文本块数
            chunks_retrieved=len(chunks),  # 检索到的文本块数
            sources=[  # 来源列表
                DocumentSource(
                    page_number=chunk.get("page_number"),  # 页码
                    similarity=chunk.get("similarity"),  # 相似度
                    preview=chunk["content"][:100] + "..."  # 内容预览（前 100 字符）
                )
                for chunk in chunks
            ] if chunks else [],  # 空列表时返回空 sources
            model=request.model or llm_service.model_main,  # 使用的模型
            rag_enabled=rag_enabled,  # 动态设置 rag_enabled
            timestamp=datetime.now(),  # 时间戳
        )

        # 构建响应
        response = ChatResponse(
            success=True,  # 操作成功
            response=ai_response,  # AI 生成的回答
            metadata=metadata,  # 元数据
        )

        logger.info(f"聊天请求处理完成: rag_enabled={rag_enabled}, chunks={len(chunks)}")

        return response

    # ====================================================================
    # 异常处理
    # ====================================================================
    except HTTPException:
        # HTTPException 直接抛出（不需要额外处理）
        raise
    except ValueError as e:
        # 参数错误
        logger.error(f"参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 其他异常
        logger.error(f"聊天失败: {e}")
        logger.exception(e)  # 添加详细堆栈信息
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天失败: {str(e)}"
        )


# ============================================================================
# 简化版聊天接口（别名）
# ============================================================================

# 新增简化版聊天端点
@router.post("")
async def chat_simple(request: ChatRequest):
    """
    简化版 RAG 聊天（兼容 /api/v1/chat 路径）

    这是 /api/v1/chat/chat 的别名，提供更简洁的 URL
    
    功能说明：
      - 与 chat_with_pdf 功能完全相同
      - 提供更简洁的 URL（/api/v1/chat 而不是 /api/v1/chat/chat）
    
    Args:
        request: 聊天请求（同 chat_with_pdf）
    
    Returns:
        聊天响应（同 chat_with_pdf）
    
    使用示例：
        POST /api/v1/chat
        {
            "pdf_id": "123e4567-e89b-12d3-a456-426614174000",
            "message": "这个文档的主要内容是什么？"
        }
    """
    return await chat_with_pdf(request)


# ============================================================================
# RAG 流程详解
# ============================================================================
# 1. 查询重写（Query Rewriting）
#    - 目的：优化用户查询，提高检索效果
#    - 方法：使用 LLM 重写查询，提取关键词
#    - 示例：
#      原始："这个文档讲了什么？"
#      重写："文档主要内容 核心观点 关键信息"
#
# 2. 向量检索（Vector Retrieval）
#    - 目的：从文档中检索相关内容
#    - 方法：计算查询向量和文档块向量的余弦相似度
#    - 返回：Top-K 个最相关的文档块
#
# 3. 上下文构建（Context Building）
#    - 目的：将检索结果格式化为 LLM prompt
#    - 方法：拼接文档块，添加来源信息
#    - 格式：
#      [来源 1 (第 3 页) | 相关度: 85.2%]
#      文档内容...
#      ---
#      [来源 2 (第 5 页) | 相关度: 78.9%]
#      文档内容...
#
# 4. LLM 生成（LLM Generation）
#    - 目的：基于检索到的上下文生成回答
#    - 方法：调用 LLM API，传入 prompt
#    - Prompt 结构：
#      系统提示词：告诉 LLM 如何使用上下文
#      用户消息：原始查询 + 检索到的上下文
#
# 5. 降级处理（Fallback）
#    - 目的：检索失败时提供友好的提示
#    - 方法：使用降级 prompt，引导用户换一种方式提问
#    - 原则：不编造不存在的内容

# ============================================================================
# 错误处理说明
# ============================================================================
# 1. PDF 不存在（404）
#    错误：HTTPException(404, "PDF 不存在")
#    原因：数据库中没有该 PDF 记录
#    解决：检查 pdf_id 是否正确
#
# 2. PDF 处理中（400）
#    错误：HTTPException(400, "PDF 文件正在处理中，请稍后再试")
#    原因：PDF 正在解析、分块、向量化
#    解决：等待处理完成（通常 1-5 分钟）
#
# 3. PDF 处理失败（400）
#    错误：HTTPException(400, "PDF 文件处理失败")
#    原因：PDF 解析失败、向量化失败等
#    解决：检查 PDF 文件是否损坏，重新上传
#
# 4. 检索失败（降级处理）
#    错误：无异常，降级为普通对话
#    原因：向量数据库查询失败、相似度过低等
#    解决：系统自动降级，引导用户换一种方式提问
#
# 5. LLM 调用失败（500）
#    错误：HTTPException(500, "AI 服务暂时不可用")
#    原因：LLM API 调用失败、超时等
#    解决：检查 LLM 服务状态，重试

# ============================================================================
# 性能优化建议
# ============================================================================
# 1. 缓存查询重写结果
#    - 使用 Redis 缓存重写结果
#    - 相同查询直接返回缓存
#
# 2. 缓存检索结果
#    - 使用 Redis 缓存检索结果
#    - 相同查询直接返回缓存
#
# 3. 批量检索
#    - 一次检索多个查询
#    - 减少数据库查询次数
#
# 4. 异步处理
#    - 使用异步 I/O
#    - 提高并发性能
#
# 5. 连接池
#    - 使用数据库连接池
#    - 减少连接开销
