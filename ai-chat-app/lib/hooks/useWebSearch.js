/**
 * ============================================================================
 * useWebSearch Hook - 联网搜索功能
 * ============================================================================
 */

'use client';

import { useState } from 'react';
import log from '@/lib/log';

export function useWebSearch() {
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);

  /**
   * 执行联网搜索
   */
  const search = async (query) => {
    setIsSearching(true);
    try {
      const response = await fetch('/api/web-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error('搜索失败');
      }

      const data = await response.json();
      setSearchResults(data.results || []);
      return data.results;
    } catch (error) {
      console.error('搜索错误:', error);
      throw error;
    } finally {
      setIsSearching(false);
    }
  };

  return {
    search,
    isSearching,
    searchResults,
  };
}
