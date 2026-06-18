import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import React, { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Field, MetricChip, PrimaryButton, SecondaryButton, SurfaceCard } from '../components/common';
import { palette } from '../constants/theme';
import { AuthState, ReadingHistoryChartTypeFacet, ReadingHistoryItem, ReadingHistoryTagFacet } from '../types/app';

function prettyChartType(value: string) {
  return value.replace(/_/g, ' ').replace(/\bsynastry\b/gi, 'relationship').replace(/\bnatal\b/gi, 'birth chart');
}

function FilterChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable style={({ pressed }) => [styles.filterChip, active && styles.filterChipActive, pressed && styles.filterChipPressed]} onPress={onPress}>
      <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>{label}</Text>
    </Pressable>
  );
}

function ReadingHistorySection({
  title,
  items,
  tagDrafts,
  setTagDrafts,
  onOpenItem,
  onToggleFavorite,
  onSaveTags,
}: {
  title: string;
  items: ReadingHistoryItem[];
  tagDrafts: Record<string, string>;
  setTagDrafts: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  onOpenItem: (item: ReadingHistoryItem) => void;
  onToggleFavorite: (item: ReadingHistoryItem) => void;
  onSaveTags: (item: ReadingHistoryItem, tags: string[]) => void;
}) {
  if (items.length === 0) return null;

  return (
    <View style={styles.sectionWrap}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {items.map((item) => {
        const tagDraft = tagDrafts[item.id] ?? item.tags.join(', ');
        return (
          <View key={item.id} style={styles.historyCard}>
            <View style={styles.historyTop}>
              <View style={styles.historyTextWrap}>
                <Text style={styles.historyHeadline}>{item.headline}</Text>
                <Text style={styles.historyMeta}>{item.subject_label} • {prettyChartType(item.chart_type)} • {new Date(item.created_at).toLocaleString()}</Text>
              </View>
              <View style={styles.historyBadge}>
                {item.chart_type === 'synastry'
                  ? <Ionicons name="people-outline" size={16} color={palette.accent} />
                  : <MaterialCommunityIcons name="orbit" size={16} color={palette.accent} />}
              </View>
            </View>
            <Text style={styles.historyStatus}>Status: {item.status}</Text>
            <View style={styles.tagWrap}>
              {item.tags.length === 0 ? <Text style={styles.muted}>No tags yet.</Text> : item.tags.map((tag) => <View key={`${item.id}-${tag}`} style={styles.tagChip}><Text style={styles.tagText}>{tag}</Text></View>)}
            </View>
            <Field
              label="Tags"
              value={tagDraft}
              onChangeText={(value) => setTagDrafts((current) => ({ ...current, [item.id]: value }))}
              placeholder="e.g. trial, relationship, shadow-work"
              autoCapitalize="none"
            />
            <View style={styles.row}>
              <View style={styles.flex}><SecondaryButton label={item.favorite ? 'Favorited' : 'Favorite'} onPress={() => onToggleFavorite(item)} icon={<Feather name="star" size={15} color={palette.ink} />} /></View>
              <View style={styles.flex}><SecondaryButton label="Save tags" onPress={() => onSaveTags(item, tagDraft.split(',').map((entry) => entry.trim()).filter(Boolean))} icon={<Feather name="tag" size={15} color={palette.ink} />} /></View>
              <View style={styles.flex}><PrimaryButton label="Open" onPress={() => onOpenItem(item)} icon={<Feather name="book-open" size={15} color={palette.white} />} /></View>
            </View>
          </View>
        );
      })}
    </View>
  );
}

export function ReadingHistoryScreen({
  authState,
  history,
  loading,
  error,
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
  onQueryChange,
  onToggleFavoriteOnly,
  onSetChartTypeFilter,
  onSetTagFilter,
  onClearFilters,
  onRefresh,
  onLoadMore,
  onOpenItem,
  onToggleFavorite,
  onSaveTags,
  onBack,
}: {
  authState: AuthState;
  history: ReadingHistoryItem[];
  loading: boolean;
  error: string | null;
  query: string;
  favoriteOnly: boolean;
  chartTypeFilter: 'all' | 'natal' | 'synastry';
  tagFilter: string | null;
  totalCount: number;
  favoritesCount: number;
  hasMore: boolean;
  visibleLimit: number;
  availableTags: ReadingHistoryTagFacet[];
  chartTypeCounts: ReadingHistoryChartTypeFacet[];
  onQueryChange: (value: string) => void;
  onToggleFavoriteOnly: () => void;
  onSetChartTypeFilter: (value: 'all' | 'natal' | 'synastry') => void;
  onSetTagFilter: (value: string | null) => void;
  onClearFilters: () => void;
  onRefresh: () => void;
  onLoadMore: () => void;
  onOpenItem: (item: ReadingHistoryItem) => void;
  onToggleFavorite: (item: ReadingHistoryItem) => void;
  onSaveTags: (item: ReadingHistoryItem, tags: string[]) => void;
  onBack: () => void;
}) {
  const [tagDrafts, setTagDrafts] = useState<Record<string, string>>({});

  const groupedHistory = useMemo(() => {
    if (favoriteOnly || chartTypeFilter !== 'all' || tagFilter || query.trim()) {
      return {
        favorites: [] as ReadingHistoryItem[],
        recent: history,
      };
    }
    return {
      favorites: history.filter((item) => item.favorite),
      recent: history.filter((item) => !item.favorite),
    };
  }, [favoriteOnly, chartTypeFilter, tagFilter, query, history]);

  const isFiltered = favoriteOnly || chartTypeFilter !== 'all' || Boolean(tagFilter) || Boolean(query.trim());

  return (
    <>
      <SurfaceCard title="Saved readings" subtitle="Use this library to revisit old readings, mark favorites, and organize them with tags.">
        <Text style={styles.body}>
          {authState.mode === 'authenticated'
            ? 'When you are signed in, readings are saved to your account and can be searched later.'
            : 'Saved reading history is available only for signed-in accounts.'}
        </Text>
      </SurfaceCard>

      <SurfaceCard title="Library summary" subtitle="A quick snapshot of what is currently saved under this account.">
        <View style={styles.metricGrid}>
          <MetricChip label="Filtered total" value={String(totalCount)} icon={<Feather name="database" size={14} color={palette.muted} />} />
          <MetricChip label="Favorites" value={String(favoritesCount)} icon={<Feather name="star" size={14} color={palette.muted} />} />
          <MetricChip label="Loaded" value={`${history.length}/${Math.max(totalCount, history.length)}`} icon={<Feather name="layers" size={14} color={palette.muted} />} />
          <MetricChip label="Page size" value={String(visibleLimit)} icon={<Feather name="list" size={14} color={palette.muted} />} />
        </View>
        {chartTypeCounts.length > 0 ? (
          <View style={styles.chartTypeSummary}>
            {chartTypeCounts.map((facet) => (
              <Text key={facet.chart_type} style={styles.summaryLine}>{prettyChartType(facet.chart_type)}: {facet.count}</Text>
            ))}
          </View>
        ) : null}
      </SurfaceCard>

      <SurfaceCard title="Search and organize" subtitle="Filter by keyword, reading type, favorite status, or tag.">
        <Field label="Search saved readings" value={query} onChangeText={onQueryChange} placeholder="Search readings or tags" autoCapitalize="none" />
        <View style={styles.filterRow}>
          <FilterChip label="All" active={chartTypeFilter === 'all'} onPress={() => onSetChartTypeFilter('all')} />
          <FilterChip label="Birth chart" active={chartTypeFilter === 'natal'} onPress={() => onSetChartTypeFilter('natal')} />
          <FilterChip label="Relationship" active={chartTypeFilter === 'synastry'} onPress={() => onSetChartTypeFilter('synastry')} />
        </View>
        <View style={styles.row}>
          <View style={styles.flex}><SecondaryButton label={favoriteOnly ? 'Showing favorites' : 'Show favorites'} onPress={onToggleFavoriteOnly} icon={<Feather name="star" size={15} color={palette.ink} />} /></View>
          <View style={styles.flex}><SecondaryButton label="Clear filters" onPress={onClearFilters} icon={<Feather name="x-circle" size={15} color={palette.ink} />} /></View>
          <View style={styles.flex}><SecondaryButton label={loading ? 'Refreshing…' : 'Refresh'} onPress={onRefresh} disabled={loading} icon={<Feather name="refresh-cw" size={15} color={palette.ink} />} /></View>
        </View>
        {availableTags.length > 0 ? (
          <View style={styles.tagFilterWrap}>
            {availableTags.map((facet) => (
              <FilterChip
                key={facet.tag}
                label={`${facet.tag} (${facet.count})`}
                active={tagFilter === facet.tag}
                onPress={() => onSetTagFilter(tagFilter === facet.tag ? null : facet.tag)}
              />
            ))}
          </View>
        ) : null}
      </SurfaceCard>

      <SurfaceCard title="Reading library" subtitle={isFiltered ? 'This is a filtered view of your saved readings.' : 'Favorites stay at the top and the rest appear in recent-first order.'}>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {history.length === 0 ? (
          <Text style={styles.muted}>{loading ? 'Loading saved readings…' : 'No saved readings match the current filter.'}</Text>
        ) : (
          <>
            <ReadingHistorySection
              title="Favorites"
              items={groupedHistory.favorites}
              tagDrafts={tagDrafts}
              setTagDrafts={setTagDrafts}
              onOpenItem={onOpenItem}
              onToggleFavorite={onToggleFavorite}
              onSaveTags={onSaveTags}
            />
            <ReadingHistorySection
              title={groupedHistory.favorites.length > 0 && groupedHistory.recent.length > 0 ? 'Recent readings' : 'Saved readings'}
              items={groupedHistory.recent}
              tagDrafts={tagDrafts}
              setTagDrafts={setTagDrafts}
              onOpenItem={onOpenItem}
              onToggleFavorite={onToggleFavorite}
              onSaveTags={onSaveTags}
            />
            {hasMore ? <PrimaryButton label={loading ? 'Loading…' : 'Load more'} onPress={onLoadMore} loading={loading} icon={<Feather name="chevrons-down" size={15} color={palette.white} />} /> : null}
          </>
        )}
      </SurfaceCard>

      <SecondaryButton label="Back" onPress={onBack} icon={<Feather name="arrow-left" size={15} color={palette.ink} />} />
    </>
  );
}

const styles = StyleSheet.create({
  body: { fontSize: 15, lineHeight: 23, color: palette.ink },
  muted: { fontSize: 14, lineHeight: 20, color: palette.muted },
  error: { fontSize: 14, lineHeight: 20, color: palette.danger },
  metricGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  chartTypeSummary: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  summaryLine: { fontSize: 13, lineHeight: 18, color: palette.muted, fontWeight: '600' },
  filterRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  filterChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.white,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  filterChipActive: {
    backgroundColor: palette.ink,
    borderColor: palette.ink,
  },
  filterChipPressed: { opacity: 0.88 },
  filterChipText: { fontSize: 12, color: palette.ink, fontWeight: '700' },
  filterChipTextActive: { color: palette.white },
  row: { flexDirection: 'row', gap: 10 },
  flex: { flex: 1 },
  tagFilterWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  sectionWrap: { gap: 14 },
  sectionTitle: { fontSize: 13, letterSpacing: 1.2, textTransform: 'uppercase', color: palette.accent, fontWeight: '700' },
  historyCard: {
    borderTopWidth: 1,
    borderTopColor: palette.border,
    paddingTop: 14,
    gap: 12,
  },
  historyTop: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  historyTextWrap: { flex: 1, gap: 5 },
  historyHeadline: { fontSize: 17, lineHeight: 23, fontWeight: '700', color: palette.ink },
  historyMeta: { fontSize: 13, lineHeight: 19, color: palette.muted },
  historyStatus: { fontSize: 13, lineHeight: 19, color: palette.ink },
  historyBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: palette.surface,
    borderWidth: 1,
    borderColor: palette.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tagWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tagChip: { borderRadius: 999, backgroundColor: palette.white, borderWidth: 1, borderColor: palette.border, paddingHorizontal: 10, paddingVertical: 7 },
  tagText: { fontSize: 12, color: palette.ink, fontWeight: '600' },
});
