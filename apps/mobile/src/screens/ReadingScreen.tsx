import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { palette } from '../constants/theme';
import { astrologyGuideSections } from '../content/astrologyGuide';
import { ChartWheel } from '../components/ChartWheel';
import { PrimaryButton, SecondaryButton, SurfaceCard } from '../components/common';
import { InterpretationCard } from '../components/InterpretationCard';
import { AnyReadingResponse, InterpretationBlock, TransitAspectRecord } from '../types/app';

function prettyLabel(value: string | null | undefined, fallback = 'Unknown') {
  if (!value) return fallback;
  return value.replace(/_/g, ' ').replace(/\basc\b/gi, 'rising sign');
}

function formatHouseRef(house?: string | null) {
  if (!house) return 'unknown house';
  return house.replace('House', 'House ');
}

function formatTransitContact(result: AnyReadingResponse, contact: TransitAspectRecord) {
  const ownerPrefix = result.chart_type === 'synastry' && contact.natal_owner !== 'self'
    ? `${contact.natal_owner === 'primary' ? 'Person A' : 'Person B'} • `
    : '';
  const timingBits = [contact.phase, contact.exact_at ? `exact ${contact.exact_at.slice(0, 16).replace('T', ' ')}` : null].filter(Boolean).join(' • ');
  return `${ownerPrefix}${contact.transit_body} ${contact.type} ${contact.natal_body} • ${contact.transit_sign} to ${contact.natal_sign} • distance from exact ${contact.orb.toFixed(1)}°${timingBits ? ` • ${timingBits}` : ''}`;
}

function simpleAspectMeaning(type: string) {
  switch (type.toLowerCase()) {
    case 'conjunction':
      return 'is strongly highlighting';
    case 'sextile':
      return 'is opening a helpful path around';
    case 'square':
      return 'is putting pressure on';
    case 'trine':
      return 'is supporting';
    case 'opposition':
      return 'is bringing a revealing tension to';
    default:
      return 'is stirring';
  }
}

function bodyTheme(body: string) {
  return {
    Sun: 'identity, purpose, and visibility',
    Moon: 'emotions, habits, and inner needs',
    Mercury: 'thinking, speech, and decisions',
    Venus: 'love, value, and connection',
    Mars: 'drive, conflict, and action',
    Jupiter: 'growth, belief, and opportunity',
    Saturn: 'duty, limits, and long-term structure',
    Asc: 'your outward style and first impression',
    MC: 'career, calling, and public direction',
  }[body] || body.toLowerCase();
}

function buildSkyNarrative(result: AnyReadingResponse, contacts: TransitAspectRecord[]) {
  if (!contacts.length) {
    return [
      'The current sky is relatively quiet around your chart right now, so this is a better time to stay with the deeper themes of the birth chart than to expect a dramatic outside push from the moment.',
    ];
  }

  const top = contacts[0];
  const firstLine = `${top.transit_body} ${simpleAspectMeaning(top.type)} your ${top.natal_body.toLowerCase()} themes, especially around ${bodyTheme(top.natal_body)}.`;

  if (result.chart_type === 'synastry') {
    const owner = top.natal_owner === 'primary' ? 'Person A' : top.natal_owner === 'secondary' ? 'Person B' : 'the relationship';
    const second = contacts[1];
    const firstParagraph = `Right now, the sky is leaning most strongly on ${owner}. ${firstLine} In plain language, this means the relationship may feel more emotionally charged, revealing, or active in that area than usual.`;
    if (!second) return [firstParagraph];
    const secondOwner = second.natal_owner === 'primary' ? 'Person A' : second.natal_owner === 'secondary' ? 'Person B' : 'the relationship';
    const secondParagraph = `${second.transit_body} ${simpleAspectMeaning(second.type)} ${secondOwner === 'the relationship' ? 'the relationship' : `${secondOwner.toLowerCase()}'s`} ${second.natal_body.toLowerCase()} themes as well, so both people may be feeling the moment in different but connected ways. The wisest response is to notice the pattern early and meet it consciously rather than react to it automatically.`;
    return [firstParagraph, secondParagraph];
  }

  const second = contacts[1];
  const firstParagraph = `Right now, ${firstLine} This is the part of life most likely to feel louder, more immediate, or more emotionally charged than usual.`;
  if (!second) return [firstParagraph];
  const secondParagraph = `${second.transit_body} ${simpleAspectMeaning(second.type)} your ${second.natal_body.toLowerCase()} themes as well, so the current sky is asking not only for awareness but also for patience, perspective, and a more conscious response in that part of your life.`;
  return [firstParagraph, secondParagraph];
}

function buildTakeaways(result: AnyReadingResponse) {
  const items: string[] = [];
  if (result.reading.headline) items.push(result.reading.headline);
  if (result.interpretation_blocks[0]?.title) items.push(result.interpretation_blocks[0].title);
  if (result.reading.timing_focus) items.push(result.reading.timing_focus);
  if (result.reading.guidance) items.push(result.reading.guidance);
  return items.slice(0, 3);
}

function buildGlossary(result: AnyReadingResponse) {
  const base = [
    { term: 'Rising sign', meaning: 'How you tend to come across at first, especially in new situations.' },
    { term: 'Sect', meaning: 'Whether the chart is a day or night chart, which changes how planets are judged in the traditional method.' },
    { term: 'House', meaning: 'The life area where a placement tends to show up most clearly.' },
    { term: 'Fortune and Spirit', meaning: 'Two traditional lots that help separate bodily or circumstantial themes from intentional or vocational ones.' },
    { term: 'Annual profection', meaning: 'A traditional timing method that activates one house and its ruler for the current year.' },
    { term: 'Solar return', meaning: 'A yearly return chart cast for the moment the Sun returns to its natal place, used to concentrate the tone of the year.' },
    { term: 'Year map', meaning: 'The app’s combined view of the activated house, the year lord, the solar return emphasis, and the Fortune/Spirit split.' },
    { term: 'Transit', meaning: 'What the planets are doing right now, and how that may affect the birth chart.' },
    { term: 'Distance from exact', meaning: 'How close a pattern is to its strongest point. Smaller usually means stronger.' },
  ];
  if (result.chart_type === 'synastry') {
    base.splice(3, 0, { term: 'Relationship pattern', meaning: 'A repeated way two people affect or respond to each other.' });
  }
  return base;
}

function buildReadingFlow(result: AnyReadingResponse) {
  return result.chart_type === 'synastry'
    ? [
        'Start with the two natal frame blocks first: they show how each person enters the bond and what their current year is activating.',
        'Then read the yearly bridge and relationship climate before deciding what the strongest cross-chart patterns mean.',
        'Use the current sky section to see why a theme may feel stronger right now.',
        'End with the practical guidance and try one small action instead of trying to absorb everything at once.',
      ]
    : [
        'Start with the big picture at the top: sect, the rising sign, and the Ascendant ruler set the frame.',
        'Then use the current year map to see the activated house, year lord, solar return tone, and whether Fortune and Spirit are aligned or split.',
        'After that, read the teaching cards as topical judgments built from house, ruler, occupants, lots, aversion, planetary witness, and repeated testimony.',
        'Use the current sky section to see what may be active right now on top of the birth chart.',
        'End with the practical guidance and try one small action instead of trying to absorb everything at once.',
      ];
}

function buildNarrativeParagraphs(result: AnyReadingResponse) {
  const paragraphs = [
    result.reading.practical_meaning,
    result.reading.psychological_meaning,
    result.reading.guidance,
    result.reading.timing_focus,
    [result.reading.ritual_focus, result.reading.prompt].filter(Boolean).join(' '),
  ].filter((value): value is string => Boolean(value && value.trim()));

  return paragraphs;
}

function buildYearMapLines(result: AnyReadingResponse) {
  if (result.chart_type !== 'natal') return [];
  const yearMap = result.technical_summary?.year_map;
  if (!yearMap) return [];
  const lines: string[] = [];
  if (yearMap.activated_house_title) {
    lines.push(
      `Activated house: ${yearMap.activated_house_title} • topics: ${yearMap.activated_topics.join(', ') || 'not specified'}`
    );
  }
  if (yearMap.lord_of_year) {
    lines.push(
      `Lord of the year: ${yearMap.lord_of_year} • ${yearMap.lord_of_year_condition ?? 'mixed'} • ${formatHouseRef(yearMap.lord_of_year_house)}`
    );
  }
  if (yearMap.solar_return_ascendant) {
    lines.push(
      `Solar return: ${yearMap.solar_return_ascendant} rising • Sun in ${formatHouseRef(yearMap.solar_return_sun_house)} • year lord in ${formatHouseRef(yearMap.solar_return_year_lord_house)}`
    );
  }
  if (yearMap.fortune_spirit_alignment) {
    lines.push(
      `Fortune and Spirit: ${prettyLabel(yearMap.fortune_spirit_alignment)}`
    );
  }
  if (yearMap.guidance) {
    lines.push(yearMap.guidance);
  }
  return lines;
}

export function ReadingScreen({
  result,
  loading,
  onEditOnboarding,
  onRefresh,
  onOpenDetail,
  onOpenAccount,
  onOpenTechnical,
}: {
  result: AnyReadingResponse;
  loading: boolean;
  onEditOnboarding: () => void;
  onRefresh: () => void;
  onOpenDetail: (block: InterpretationBlock) => void;
  onOpenAccount: () => void;
  onOpenTechnical: () => void;
}) {
  const [activeTab, setActiveTab] = useState<'reading' | 'guide'>('reading');
  const takeaways = buildTakeaways(result);
  const glossary = buildGlossary(result);
  const readingFlow = buildReadingFlow(result);
  const narrativeParagraphs = buildNarrativeParagraphs(result);
  const transitContacts = result.chart_type === 'synastry'
    ? [
        ...(result.technical_summary?.primary_transit_aspects ?? []),
        ...(result.technical_summary?.secondary_transit_aspects ?? []),
      ].sort((a, b) => a.orb - b.orb)
    : (result.technical_summary?.transit_aspects ?? []);
  const skyNarrative = buildSkyNarrative(result, transitContacts);
  const yearMapLines = buildYearMapLines(result);

  const transitStamp = result.technical_summary?.transit_timestamp
    ? `${result.technical_summary.transit_timestamp.slice(0, 16).replace('T', ' ')}${result.technical_summary?.transit_timezone ? ` • ${result.technical_summary.transit_timezone}` : ''}`
    : null;

  return (
    <>
      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>{result.chart_type === 'synastry' ? 'Relationship Reading' : 'Natal Reading'}</Text>
        <Text style={styles.title}>{result.reading.headline}</Text>
        {result.reading.oracle ? <Text style={styles.oracle}>{result.reading.oracle}</Text> : null}
        {narrativeParagraphs.map((paragraph, index) => <Text key={`${index}-${paragraph.slice(0, 24)}`} style={styles.body}>{paragraph}</Text>)}
      </View>

      <View style={styles.tabWrap}>
        <Pressable style={[styles.tabPill, activeTab === 'reading' && styles.tabPillActive]} onPress={() => setActiveTab('reading')}>
          <Text style={[styles.tabText, activeTab === 'reading' && styles.tabTextActive]}>Reading</Text>
        </Pressable>
        <Pressable style={[styles.tabPill, activeTab === 'guide' && styles.tabPillActive]} onPress={() => setActiveTab('guide')}>
          <Text style={[styles.tabText, activeTab === 'guide' && styles.tabTextActive]}>Guide</Text>
        </Pressable>
      </View>

      {activeTab === 'reading' && result.prediction_cards?.length ? (
        <>
          {yearMapLines.length ? (
            <SurfaceCard title="Current year map" subtitle="This combines the profection year, solar return, and Fortune/Spirit into one timing frame.">
              <View style={styles.flowStack}>
                {yearMapLines.map((line) => (
                  <Text key={line} style={styles.flowText}>• {line}</Text>
                ))}
              </View>
            </SurfaceCard>
          ) : null}

        <SurfaceCard title="What to expect next" subtitle="This section translates the chart into practical near-term guidance in plain language.">
          <View style={styles.predictionStack}>
            {result.prediction_cards.map((card) => (
              <View key={card.key} style={styles.predictionCard}>
                <View style={styles.predictionHeader}>
                  <Text style={styles.predictionTimeframe}>{card.timeframe}</Text>
                  <Text style={styles.predictionTitle}>{card.title}</Text>
                </View>
                <Text style={styles.predictionSummary}>{card.summary}</Text>
                {card.opportunities.length ? <Text style={styles.predictionList}><Text style={styles.predictionLabel}>Helpful openings:</Text> {card.opportunities.join(' • ')}</Text> : null}
                {card.cautions.length ? <Text style={styles.predictionList}><Text style={styles.predictionLabel}>What to watch for:</Text> {card.cautions.join(' • ')}</Text> : null}
                {card.rituals.length ? <Text style={styles.predictionList}><Text style={styles.predictionLabel}>Try this:</Text> {card.rituals.join(' • ')}</Text> : null}
                {card.citations.length ? <Text style={styles.predictionCitations}>{card.citations.join(' • ')}</Text> : null}
              </View>
            ))}
          </View>
        </SurfaceCard>
        </>
      ) : null}

      {activeTab === 'reading' && transitContacts.length ? (
        <SurfaceCard title="Sky Chart" subtitle="This section explains what the current sky is emphasizing in plain language.">
          {transitStamp ? <Text style={styles.transitStamp}>{transitStamp}</Text> : null}
          <View style={styles.transitStack}>
            {skyNarrative.map((paragraph, index) => (
              <View key={`${index}-${paragraph.slice(0, 20)}`} style={styles.transitCard}>
                <Text style={styles.transitSummary}>{paragraph}</Text>
              </View>
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      {activeTab === 'reading' ? (
        <SurfaceCard title="Chart map" subtitle="Think of this as a visual map of the reading. You do not need to decode every symbol at once.">
          <Text style={styles.chartHelper}>The chart shows where the main patterns sit. Use it to orient yourself, then use the written reading to understand what matters most.</Text>
          <ChartWheel
            title={result.chart_type === 'synastry' ? 'Relationship chart map' : 'Birth chart map'}
            primaryChart={result.chart_type === 'synastry' ? result.technical_summary?.primary_chart_data : result.technical_summary?.chart_data}
            secondaryChart={result.chart_type === 'synastry' ? result.technical_summary?.secondary_chart_data : result.technical_summary?.transit_chart_data}
            compact
          />
          <SecondaryButton label="Open full chart details" onPress={onOpenTechnical} icon={<MaterialCommunityIcons name="chart-bubble" size={17} color={palette.ink} />} />
        </SurfaceCard>
      ) : null}

      {activeTab === 'reading' ? (
        <SurfaceCard title="Learn each part of your reading" subtitle="Tap any card for a more focused explanation of that placement or pattern.">
          {result.interpretation_blocks.map((block) => (
            <InterpretationCard key={`${block.block_type}-${block.title}`} block={block} onPress={() => onOpenDetail(block)} />
          ))}
        </SurfaceCard>
      ) : null}

      {activeTab === 'guide' ? (
        <>
          <SurfaceCard title="How to read this page" subtitle="The app keeps the advanced material, but it teaches you in a simple order.">
            <View style={styles.flowStack}>
              {readingFlow.map((step, index) => (
                <Text key={step} style={styles.flowText}><Text style={styles.flowIndex}>{index + 1}. </Text>{step}</Text>
              ))}
            </View>
          </SurfaceCard>

          <SurfaceCard title="If you remember only three things" subtitle="This is the shortest version of the reading.">
            <View style={styles.flowStack}>
              {takeaways.map((item) => <Text key={item} style={styles.flowText}>• {item}</Text>)}
            </View>
          </SurfaceCard>

          <SurfaceCard title="Quick term guide" subtitle="A few short definitions so the app can teach without hiding the real terms.">
            <View style={styles.glossaryWrap}>
              {glossary.map((item) => (
                <View key={item.term} style={styles.glossaryCard}>
                  <Text style={styles.glossaryTerm}>{item.term}</Text>
                  <Text style={styles.glossaryMeaning}>{item.meaning}</Text>
                </View>
              ))}
            </View>
          </SurfaceCard>

          <SurfaceCard title="Astrology and The Ark guide" subtitle="This longer guide explains the system, the language, and how this app works.">
            <View style={styles.docSectionWrap}>
              {astrologyGuideSections.map((section) => (
                <View key={section.title} style={styles.docSection}>
                  <Text style={styles.docTitle}>{section.title}</Text>
                  {section.paragraphs?.map((paragraph) => (
                    <Text key={paragraph} style={styles.docParagraph}>{paragraph}</Text>
                  ))}
                  {section.bullets?.map((bullet) => (
                    <Text key={bullet} style={styles.docBullet}>• {bullet}</Text>
                  ))}
                </View>
              ))}
            </View>
          </SurfaceCard>

        </>
      ) : null}

      {activeTab === 'reading' && result.source_lenses?.length ? (
        <SurfaceCard title="How this reading was interpreted" subtitle="These are the frameworks The Ark used while building the reading.">
          <View style={styles.lensWrap}>
            {result.source_lenses.map((lens) => (
              <View key={lens.lens} style={styles.lensCard}>
                <Text style={styles.lensTitle}>{prettyLabel(lens.lens).toUpperCase()}</Text>
                <Text style={styles.lensText}>{lens.labels.join(' • ')}</Text>
              </View>
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      {activeTab === 'reading' ? (
        <SurfaceCard title="Notes from the app" subtitle="These notes explain anything the app had to estimate, simplify, or handle behind the scenes.">
          {result.notes.map((note) => (
            <Text key={note} style={styles.note}>• {note}</Text>
          ))}
        </SurfaceCard>
      ) : null}

      {activeTab === 'reading' ? (
        <>
          <View style={styles.row}>
            <View style={styles.flex}><SecondaryButton label="Edit birth details" onPress={onEditOnboarding} icon={<Feather name="edit-3" size={15} color={palette.ink} />} /></View>
            <View style={styles.flex}><PrimaryButton label="Refresh reading" onPress={onRefresh} loading={loading} icon={<Feather name="refresh-cw" size={15} color={palette.white} />} /></View>
          </View>
          <SecondaryButton label="Account and settings" onPress={onOpenAccount} icon={<Ionicons name="person-circle-outline" size={17} color={palette.ink} />} />
        </>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  heroCard: {
    backgroundColor: palette.surface,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: palette.border,
    padding: 24,
    gap: 12,
  },
  eyebrow: { fontSize: 10, letterSpacing: 1.7, textTransform: 'uppercase', color: palette.muted, fontWeight: '700' },
  title: { fontSize: 30, lineHeight: 38, color: palette.ink, fontWeight: '700' },
  oracle: { fontSize: 13, lineHeight: 20, color: palette.ink, fontWeight: '600' },
  body: { fontSize: 15, lineHeight: 24, color: palette.ink },
  tabWrap: {
    flexDirection: 'row',
    gap: 6,
    backgroundColor: palette.surface,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 16,
    padding: 5,
  },
  tabPill: {
    flex: 1,
    minHeight: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabPillActive: { backgroundColor: palette.accent },
  tabText: { fontSize: 13, lineHeight: 17, fontWeight: '700', color: palette.muted },
  tabTextActive: { color: palette.white },
  predictionStack: { gap: 14 },
  transitStamp: { fontSize: 11, lineHeight: 17, color: palette.muted, fontWeight: '700' },
  transitStack: { gap: 12 },
  chartHelper: { fontSize: 14, lineHeight: 21, color: palette.muted },
  transitCard: { backgroundColor: palette.surface, borderWidth: 1, borderColor: palette.border, borderRadius: 16, padding: 16, gap: 6 },
  transitTitle: { fontSize: 16, lineHeight: 21, color: palette.ink, fontWeight: '700' },
  transitSummary: { fontSize: 14, lineHeight: 21, color: palette.muted },
  predictionCard: { backgroundColor: palette.surface, borderWidth: 1, borderColor: palette.border, borderRadius: 16, padding: 18, gap: 10 },
  predictionHeader: { gap: 5 },
  predictionTimeframe: { fontSize: 10, letterSpacing: 1.4, textTransform: 'uppercase', color: palette.muted, fontWeight: '700' },
  predictionTitle: { fontSize: 20, lineHeight: 26, color: palette.ink, fontWeight: '700' },
  predictionSummary: { fontSize: 15, lineHeight: 22, color: palette.ink },
  predictionList: { fontSize: 13, lineHeight: 20, color: palette.muted },
  predictionLabel: { color: palette.ink, fontWeight: '700' },
  predictionCitations: { fontSize: 12, lineHeight: 18, color: palette.muted },
  lensWrap: { gap: 12 },
  lensCard: { backgroundColor: palette.surface, borderWidth: 1, borderColor: palette.border, borderRadius: 14, padding: 16, gap: 7 },
  lensTitle: { fontSize: 11, letterSpacing: 1.3, textTransform: 'uppercase', color: palette.ink, fontWeight: '700' },
  lensText: { fontSize: 13, lineHeight: 20, color: palette.muted },
  metricGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  note: { fontSize: 14, lineHeight: 21, color: palette.muted },
  flowStack: { gap: 10 },
  flowText: { fontSize: 14, lineHeight: 22, color: palette.ink },
  flowIndex: { color: palette.accent, fontWeight: '700' },
  glossaryWrap: { gap: 12 },
  glossaryCard: { backgroundColor: palette.surface, borderWidth: 1, borderColor: palette.border, borderRadius: 14, padding: 16, gap: 6 },
  glossaryTerm: { fontSize: 15, lineHeight: 21, color: palette.ink, fontWeight: '700' },
  glossaryMeaning: { fontSize: 13, lineHeight: 20, color: palette.muted },
  docSectionWrap: { gap: 18 },
  docSection: { gap: 10, paddingBottom: 8, borderBottomWidth: 1, borderBottomColor: palette.border },
  docTitle: { fontSize: 18, lineHeight: 24, color: palette.ink, fontWeight: '700' },
  docParagraph: { fontSize: 15, lineHeight: 23, color: palette.ink },
  docBullet: { fontSize: 14, lineHeight: 22, color: palette.muted },
  row: { flexDirection: 'row', gap: 10 },
  flex: { flex: 1 },
});
