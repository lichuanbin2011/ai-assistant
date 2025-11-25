/**
 * ============================================================================
 * 引用来源卡片组件 (app/components/chat/CitationCard.js)
 * ============================================================================
 *
 * 文件作用：
 *   显示 AI 联网搜索的引用来源，支持折叠/展开
 *
 * 主要功能：
 *   1. 显示搜索来源列表
 *   2. 支持折叠/展开切换
 *   3. 点击跳转到原始网页
 *   4. 显示来源摘要和元信息
 *
 * 使用场景：
 *   在 MessageItem 组件中显示 AI 回复的引用来源
 *
 * 修改记录：
 *   - 2025-11-15：添加数据验证和调试日志
 *   - 优化样式和交互体验
 *   - 修复潜在的数据类型错误
 *
 * ============================================================================
 */

'use client';

import { useState, useEffect } from 'react'; //  新增 useEffect
import {
  ExternalLink,
  FileText,
  ChevronDown,
  ChevronUp,
  Globe,
} from 'lucide-react';
import log from '@/lib/log';

/**
 * CitationCard - 引用来源卡片组件
 *
 * @param {Object} props
 * @param {Array} props.citations - 引用来源数组
 * @param {boolean} props.defaultExpanded - 默认是否展开（可选，默认 false）
 *
 * citations 数据结构：
 * [
 *   {
 *     index: 1,                    // 引用序号
 *     title: "标题",               // 来源标题
 *     url: "https://...",          // 来源链接
 *     snippet: "摘要内容...",      // 内容摘要
 *     siteName: "网站名称",        // 网站名称（可选）
 *     dateLastCrawled: "2024-01-01" // 抓取日期（可选）
 *   }
 * ]
 */
export default function CitationCard({ citations, defaultExpanded = false }) {
  // ========================================================================
  // 1. 状态管理
  // ========================================================================
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // ========================================================================
  // 2. 数据验证和调试
  // ========================================================================

  //  新增：调试日志（仅开发环境）
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      log.debug('🔍 CitationCard 接收到的数据:', {
        citations,
        citationsType: typeof citations,
        isArray: Array.isArray(citations),
        citationsLength: citations?.length || 0,
        firstCitation: citations?.[0],
      });
    }
  }, [citations]);

  //  修改：更严格的数据验证
  if (!citations) {
    console.warn('⚠️ CitationCard: citations 为 null 或 undefined');
    return null;
  }

  if (!Array.isArray(citations)) {
    console.error('❌ CitationCard: citations 不是数组类型', typeof citations);
    return (
      <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
        ⚠️ 引用来源数据格式错误（期望数组，实际为 {typeof citations}）
      </div>
    );
  }

  if (citations.length === 0) {
    console.warn('⚠️ CitationCard: citations 数组为空');
    return null;
  }

  //  新增：数据清洗（过滤无效数据）
  const validCitations = citations.filter((citation) => {
    const isValid =
      citation && citation.url && (citation.title || citation.snippet);
    if (!isValid && process.env.NODE_ENV === 'development') {
      console.warn('⚠️ 过滤无效引用:', citation);
    }
    return isValid;
  });

  if (validCitations.length === 0) {
    console.warn('⚠️ CitationCard: 没有有效的引用来源');
    return (
      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-700">
        ⚠️ 引用来源数据不完整（缺少必要字段）
      </div>
    );
  }

  // ========================================================================
  // 3. 渲染组件
  // ========================================================================
  return (
    <div className="mt-4 border-t border-gray-200 pt-4">
      {/*  调试信息（仅开发环境） */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mb-2 p-2 bg-gray-100 rounded text-xs font-mono text-gray-600">
          [DEBUG] 有效引用: {validCitations.length} / {citations.length}
        </div>
      )}

      {/* 标题栏 - 可点击折叠/展开 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-sm font-semibold text-gray-700 hover:text-gray-900 transition-colors mb-3 group"
        aria-expanded={isExpanded}
        aria-label={isExpanded ? '折叠引用来源' : '展开引用来源'}
      >
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-500" />
          <span>消息来源</span>
          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
            {validCitations.length}
          </span>
        </div>

        {/* 折叠/展开图标 */}
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
        )}
      </button>

      {/* 折叠状态 - 显示简略信息 */}
      {!isExpanded && (
        <div className="text-xs text-gray-500 pl-6">
          来自{' '}
          {validCitations
            .slice(0, 3)
            .map((c) => c.siteName || '网页')
            .join('、')}
          {validCitations.length > 3 && ` 等 ${validCitations.length} 个来源`}
        </div>
      )}

      {/* 展开状态 - 显示完整来源列表 */}
      {isExpanded && (
        <div className="space-y-2">
          {validCitations.map((citation, idx) => (
            <a
              key={citation.index || idx}
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 bg-gradient-to-r from-blue-50 to-transparent rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all group/citation"
              aria-label={`打开引用来源: ${citation.title || citation.name || '未命名来源'}`}
            >
              <div className="flex items-start gap-3">
                {/* 引用序号 */}
                <span className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold shadow-sm">
                  {citation.index || idx + 1}
                </span>

                {/* 来源内容 */}
                <div className="flex-1 min-w-0">
                  {/* 标题和外链图标 */}
                  <div className="flex items-center gap-2 mb-1">
                    <h5 className="text-sm font-medium text-gray-900 truncate group-hover/citation:text-blue-600 transition-colors">
                      {citation.title || citation.name || '未命名来源'}
                    </h5>
                    <ExternalLink className="h-3 w-3 text-gray-400 group-hover/citation:text-blue-600 flex-shrink-0 transition-colors" />
                  </div>

                  {/* 摘要内容 */}
                  {citation.snippet && (
                    <p className="mt-1 text-xs text-gray-600 line-clamp-2 leading-relaxed">
                      {citation.snippet}
                    </p>
                  )}

                  {/* 元信息（网站名称、日期、URL） */}
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                    {/* 网站名称 */}
                    {citation.siteName && (
                      <span className="flex items-center gap-1">
                        <Globe className="h-3 w-3" />
                        {citation.siteName}
                      </span>
                    )}

                    {/* 抓取日期 */}
                    {citation.dateLastCrawled && (
                      <span>
                        {(() => {
                          try {
                            return new Date(
                              citation.dateLastCrawled
                            ).toLocaleDateString('zh-CN', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            });
                          } catch (error) {
                            console.warn(
                              '⚠️ 日期格式错误:',
                              citation.dateLastCrawled
                            );
                            return citation.dateLastCrawled;
                          }
                        })()}
                      </span>
                    )}

                    {/* URL（截断显示） */}
                    {citation.url && (
                      <span className="truncate max-w-xs text-gray-400">
                        {citation.url.replace(/^https?:\/\//, '').split('/')[0]}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
