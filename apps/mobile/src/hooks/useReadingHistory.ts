import { useEffect, useState } from 'react';
import { fetchReadingHistory, fetchReadingHistoryItem, updateReadingHistoryItem } from '../services/api';
import { AuthState, ReadingHistoryChartTypeFacet, ReadingHistoryItem, ReadingHistoryTagFacet } from '../types/app';

const DEFAULT_VISIBLE_LIMIT = 20;

type RefreshOptions = {
  apiBaseUrl?: string;
  preserveVisibleCount?: boolean;
  visibleLimit?: number;
  overrideQuery?: string;
  overrideFavoriteOnly?: boolean;
  overrideChartType?: 'all' | 'natal' | 'synastry';
  overrideTag?: string | null;
};

export function useReadingHistory(authState: AuthState) {
  const [history, setHistory] = useState<ReadingHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [favoriteOnly, setFavoriteOnly] = useState(false);
  const [chartTypeFilter, setChartTypeFilter] = useState<'all' | 'natal' | 'synastry'>('all');
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [visibleLimit, setVisibleLimit] = useState(DEFAULT_VISIBLE_LIMIT);
  const [totalCount, setTotalCount] = useState(0);
  const [favoritesCount, setFavoritesCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [availableTags, setAvailableTags] = useState<ReadingHistoryTagFacet[]>([]);
  const [chartTypeCounts, setChartTypeCounts] = useState<ReadingHistoryChartTypeFacet[]>([]);

  async function refreshHistory(options: RefreshOptions = {}) {
    const effectiveBaseUrl = options.apiBaseUrl || authState.apiBaseUrl || '';
    if (authState.mode !== 'authenticated' || !authState.token || !effectiveBaseUrl) {
      setHistory([]);
      setTotalCount(0);
      setFavoritesCount(0);
      setHasMore(false);
      setAvailableTags([]);
      setChartTypeCounts([]);
      return [];
    }

    const requestedVisibleLimit = options.visibleLimit
      ?? (options.preserveVisibleCount ? Math.max(history.length || visibleLimit, visibleLimit) : visibleLimit);

    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const response = await fetchReadingHistory(effectiveBaseUrl, authState.token, {
        query: options.overrideQuery ?? query,
        favoriteOnly: options.overrideFavoriteOnly ?? favoriteOnly,
        chartType: options.overrideChartType ?? chartTypeFilter,
        tag: options.overrideTag ?? tagFilter,
        offset: 0,
        limit: requestedVisibleLimit,
      });
      setHistory(response.items);
      setVisibleLimit(response.limit);
      setTotalCount(response.total);
      setFavoritesCount(response.favorites_count);
      setHasMore(response.has_more);
      setAvailableTags(response.available_tags);
      setChartTypeCounts(response.chart_type_counts);
      return response.items;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not load account reading history.';
      setHistoryError(message);
      throw err;
    } finally {
      setHistoryLoading(false);
    }
  }

  async function loadMoreHistory(apiBaseUrl?: string) {
    if (!hasMore) {
      return history;
    }
    return refreshHistory({
      apiBaseUrl,
      preserveVisibleCount: true,
      visibleLimit: visibleLimit + DEFAULT_VISIBLE_LIMIT,
    });
  }

  async function loadHistoryItem(readingId: string, apiBaseUrl?: string) {
    if (authState.mode !== 'authenticated' || !authState.token || !(apiBaseUrl || authState.apiBaseUrl)) {
      throw new Error('Sign in to load account reading history.');
    }
    const response = await fetchReadingHistoryItem(apiBaseUrl || authState.apiBaseUrl || '', authState.token, readingId);
    return response.item;
  }

  async function loadLatestHistoryItem(chartType: 'natal' | 'synastry' = 'natal', apiBaseUrl?: string) {
    if (authState.mode !== 'authenticated' || !authState.token || !(apiBaseUrl || authState.apiBaseUrl)) {
      return null;
    }
    const response = await fetchReadingHistory(apiBaseUrl || authState.apiBaseUrl || '', authState.token, {
      chartType,
      offset: 0,
      limit: 1,
    });
    return response.items[0] ?? null;
  }

  async function saveHistoryMetadata(readingId: string, updates: { favorite?: boolean; tags?: string[] }, apiBaseUrl?: string) {
    if (authState.mode !== 'authenticated' || !authState.token || !(apiBaseUrl || authState.apiBaseUrl)) {
      throw new Error('Sign in to update reading history metadata.');
    }
    const effectiveBaseUrl = apiBaseUrl || authState.apiBaseUrl || '';
    const response = await updateReadingHistoryItem(effectiveBaseUrl, authState.token, readingId, updates);
    await refreshHistory({ apiBaseUrl: effectiveBaseUrl, preserveVisibleCount: true }).catch(() => []);
    return response.item;
  }

  useEffect(() => {
    if (authState.mode !== 'authenticated' || !authState.token || !authState.apiBaseUrl) {
      setHistory([]);
      setTotalCount(0);
      setFavoritesCount(0);
      setHasMore(false);
      setAvailableTags([]);
      setChartTypeCounts([]);
      setVisibleLimit(DEFAULT_VISIBLE_LIMIT);
      return;
    }
    const timer = setTimeout(() => {
      void refreshHistory({ apiBaseUrl: authState.apiBaseUrl }).catch(() => {});
    }, 220);
    return () => clearTimeout(timer);
  }, [authState.mode, authState.token, authState.apiBaseUrl, query, favoriteOnly, chartTypeFilter, tagFilter]);

  return {
    history,
    historyLoading,
    historyError,
    query,
    favoriteOnly,
    chartTypeFilter,
    tagFilter,
    totalCount,
    favoritesCount,
    hasMore,
    visibleLimit,
    availableTags,
    chartTypeCounts,
    setHistoryError,
    setQuery,
    toggleFavoriteOnly: () => setFavoriteOnly((current) => !current),
    setChartTypeFilter,
    setTagFilter,
    clearFilters: () => {
      setQuery('');
      setFavoriteOnly(false);
      setChartTypeFilter('all');
      setTagFilter(null);
      setVisibleLimit(DEFAULT_VISIBLE_LIMIT);
    },
    refreshHistory,
    loadMoreHistory,
    loadHistoryItem,
    loadLatestHistoryItem,
    saveHistoryMetadata,
  };
}
