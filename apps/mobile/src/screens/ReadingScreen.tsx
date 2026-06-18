import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import React, { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { GlossaryText } from '../components/GlossaryText';
import { ChartWheel } from '../components/ChartWheel';
import { InterpretationCard } from '../components/InterpretationCard';
import { PrimaryButton, SecondaryButton, SurfaceCard } from '../components/common';
import { palette } from '../constants/theme';
import { astrologyGuideSections } from '../content/astrologyGuide';
import { GLOSSARY_ENTRIES } from '../content/glossary';
import { AnyReadingResponse, InterpretationBlock, TopicJudgmentRecord, TransitAspectRecord } from '../types/app';

function formatHouseRef(house?: string | null) {
  if (!house) return 'an unknown house';
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

function bodyLabel(body: string) {
  return {
    Sun: 'Sun matters',
    Moon: 'Moon matters',
    Mercury: 'Mercury matters',
    Venus: 'Venus matters',
    Mars: 'Mars matters',
    Jupiter: 'Jupiter matters',
    Saturn: 'Saturn matters',
    Asc: 'your Ascendant',
    MC: 'your Midheaven',
  }[body] || `${body} matters`;
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
      'The current sky is relatively quiet around your chart right now, so this is a better time to stay with the deeper annual and natal themes than to expect a dramatic outside push from the moment.',
    ];
  }

  const top = contacts[0];
  const firstLine = `${top.transit_body} ${simpleAspectMeaning(top.type)} ${bodyLabel(top.natal_body)}, especially ${bodyTheme(top.natal_body)}.`;

  if (result.chart_type === 'synastry') {
    const owner = top.natal_owner === 'primary' ? 'Person A' : top.natal_owner === 'secondary' ? 'Person B' : 'the relationship';
    const second = contacts[1];
    const firstParagraph = `Right now, the sky is leaning most strongly on ${owner}. ${firstLine} The relationship may feel more emotionally charged, revealing, or active in that area than usual.`;
    if (!second) return [firstParagraph];
    const secondOwner = second.natal_owner === 'primary' ? 'Person A' : second.natal_owner === 'secondary' ? 'Person B' : 'the relationship';
    const secondParagraph = `${second.transit_body} ${simpleAspectMeaning(second.type)} ${secondOwner === 'the relationship' ? 'the relationship dynamic' : `${secondOwner.toLowerCase()}'s ${bodyLabel(second.natal_body)}`} as well, so both people may be feeling the moment in different but connected ways.`;
    return [firstParagraph, secondParagraph];
  }

  const second = contacts[1];
  const firstParagraph = `Right now, ${firstLine} This is the part of life most likely to feel louder, more immediate, or more emotionally charged than usual.`;
  if (!second) return [firstParagraph];
  const secondParagraph = `${second.transit_body} ${simpleAspectMeaning(second.type)} ${bodyLabel(second.natal_body)} as well, so the current sky is asking for awareness, patience, and a more conscious response in that part of your life.`;
  return [firstParagraph, secondParagraph];
}

function dedupeBlocks(blocks: InterpretationBlock[]) {
  const seen = new Set<string>();
  return [...blocks]
    .sort((a, b) => (a.display_priority ?? 100) - (b.display_priority ?? 100))
    .filter((block) => {
      const key = block.repeat_key || `${block.block_type}:${block.topic_key || block.title}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function blockByType(blocks: InterpretationBlock[], blockType: string) {
  return blocks.find((block) => block.block_type === blockType);
}

function sortedTopics(result: AnyReadingResponse) {
  return [...(result.technical_summary?.topic_judgments ?? [])].sort((a, b) => b.score - a.score);
}

function confidenceExplainer(topic?: TopicJudgmentRecord | null) {
  if (!topic) return null;
  if (topic.confidence === 'high') return 'High confidence means several traditional factors point in the same direction.';
  if (topic.confidence === 'medium' && topic.classification === 'mixed') return 'Medium confidence here means the chart shows both support and friction, and several factors repeat that mixed picture.';
  if (topic.confidence === 'medium') return 'Medium confidence means several factors point this way, but the testimony is not unanimous.';
  return 'Low confidence means the chart offers a clue, but the testimony is still thin or divided.';
}

function topicSummary(topic?: TopicJudgmentRecord | null) {
  if (!topic) return null;
  if (topic.classification === 'supportive') {
    return `${topic.title} is the most supported area right now. The chart gives repeated help here rather than leaving the topic to stand alone.`;
  }
  if (topic.classification === 'difficult') {
    return `${topic.title} is the area asking for the most care. This does not guarantee failure, but it does mean the chart shows repeated friction, cost, or pressure here.`;
  }
  return `${topic.title} shows mixed testimony. The chart gives both support and friction here, so the story is not simple or one-sided.`;
}

function buildOpeningSummary(result: AnyReadingResponse, strongest?: TopicJudgmentRecord | null, strained?: TopicJudgmentRecord | null) {
  const yearMap = result.chart_type === 'natal' ? result.technical_summary?.year_map : null;
  if (!yearMap) {
    return {
      title: result.reading.headline,
      paragraphs: [
        result.reading.practical_meaning,
        result.reading.life_translation,
        result.reading.guidance,
      ].filter(Boolean),
      testimony: null as string | null,
    };
  }

  const topicText = yearMap.activated_topics.length
    ? yearMap.activated_topics.join(', ')
    : 'the active house topics';
  const title = `This is a ${yearMap.activated_house_title || 'current'} year ruled by ${yearMap.lord_of_year || 'its year lord'}.`;
  const paragraphs = [
    `The year keeps drawing attention to ${topicText}. The emphasis is less about isolated events and more about the themes that keep repeating until they are understood and handled consciously.`,
    yearMap.lord_of_year
      ? `${yearMap.lord_of_year} carries the year from ${formatHouseRef(yearMap.lord_of_year_house)}, so that part of life becomes the place where the annual storyline is most likely to become visible, manageable, or meaningful.`
      : null,
    yearMap.fortune_spirit_alignment === 'split'
      ? 'Fortune and Spirit are split, which means circumstances and chosen direction may not be telling the same story. What life demands materially may differ from what you most want to pursue intentionally.'
      : yearMap.fortune_spirit_alignment === 'aligned'
        ? 'Fortune and Spirit are aligned, so circumstances and chosen direction are reinforcing each other more than usual.'
        : null,
    strongest && strained
      ? `The chart looks most supportive around ${strongest.title.toLowerCase()} and most pressured around ${strained.title.toLowerCase()}, so the year is not flat. It has clear areas of help and clear areas asking for care.`
      : null,
  ].filter((value): value is string => Boolean(value));

  let testimony = 'The testimony is mixed.';
  if (strongest && strongest.classification === 'supportive' && strained && strained.classification === 'difficult') {
    testimony = 'The chart shows both support and strain.';
  }
  return { title, paragraphs, testimony };
}

function buildReadingFlow(result: AnyReadingResponse) {
  return result.chart_type === 'synastry'
    ? [
        'Start with the opening summary so you know the relationship story before reading the technique.',
        'Then move through the relationship cards one concept at a time instead of trying to decode every term at once.',
        'Use the sky card as short-term weather, not the whole relationship reading.',
        'Open the evidence only when you want to see exactly why the app is making a claim.',
      ]
    : [
        'Start with the opening summary first, before looking at the doctrine.',
        'Then read the timing technique card so you know why this year has its current emphasis.',
        'Use the planet, Fortune/Spirit, and support/strain cards to see what matters most.',
        'Treat the current sky as temporary weather layered on top of the larger year map.',
        'Open the technical drawer only when you want the explicit calculation trail.',
      ];
}

function learnCardsForGuide(blocks: InterpretationBlock[]) {
  return blocks
    .filter((block) => block.technical_terms?.length || block.traditional_doctrine || block.plain_meaning)
    .slice(0, 8);
}

function CollapsibleCard({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <SurfaceCard title={title} subtitle={subtitle}>
      <Pressable onPress={() => setOpen((value) => !value)} style={styles.collapseToggle}>
        <Text style={styles.collapseToggleText}>{open ? 'Hide details' : 'Show details'}</Text>
        <Feather name={open ? 'chevron-up' : 'chevron-down'} size={16} color={palette.ink} />
      </Pressable>
      {open ? children : null}
    </SurfaceCard>
  );
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
  const blocks = useMemo(() => dedupeBlocks(result.interpretation_blocks), [result.interpretation_blocks]);
  const annualBlock = blockByType(blocks, 'annual_profection');
  const yearMapBlock = blockByType(blocks, 'year_map');
  const fortuneBlock = blockByType(blocks, 'fortune_spirit');
  const solarReturnBlock = blockByType(blocks, 'solar_return');
  const topicBlocks = blocks.filter((block) => block.block_type === 'topic_judgment');
  const topicJudgments = sortedTopics(result);
  const strongest = topicJudgments[0] ?? null;
  const strained = topicJudgments.length > 1 ? topicJudgments[topicJudgments.length - 1] : topicJudgments[0] ?? null;
  const openingSummary = buildOpeningSummary(result, strongest, strained);
  const transitContacts = result.chart_type === 'synastry'
    ? [
        ...(result.technical_summary?.primary_transit_aspects ?? []),
        ...(result.technical_summary?.secondary_transit_aspects ?? []),
      ].sort((a, b) => a.orb - b.orb)
    : (result.technical_summary?.transit_aspects ?? []);
  const skyNarrative = buildSkyNarrative(result, transitContacts);
  const transitStamp = result.technical_summary?.transit_timestamp
    ? `${result.technical_summary.transit_timestamp.slice(0, 16).replace('T', ' ')}${result.technical_summary?.transit_timezone ? ` • ${result.technical_summary.transit_timezone}` : ''}`
    : null;
  const readingFlow = buildReadingFlow(result);
  const guideCards = learnCardsForGuide(blocks);
  const technicalLines = [
    result.technical_summary?.house_system ? `House system: ${result.technical_summary.house_system}` : null,
    result.technical_summary?.chart_data?.traditional_context?.sect ? `Sect: ${result.technical_summary.chart_data.traditional_context.sect}` : null,
    result.technical_summary?.chart_data?.traditional_context?.ascendant_sign ? `Ascendant: ${result.technical_summary.chart_data.traditional_context.ascendant_sign}` : null,
    result.technical_summary?.annual_profection?.activated_house ? `Activated house: House ${result.technical_summary.annual_profection.activated_house}` : null,
    result.technical_summary?.annual_profection?.lord_of_year ? `Lord of the year: ${result.technical_summary.annual_profection.lord_of_year}` : null,
    result.technical_summary?.solar_return?.return_ascendant_sign ? `Solar return ascendant: ${result.technical_summary.solar_return.return_ascendant_sign}` : null,
    result.technical_summary?.chart_data?.traditional_context?.fortune ? `Fortune: ${result.technical_summary.chart_data.traditional_context.fortune.sign} ${formatHouseRef(result.technical_summary.chart_data.traditional_context.fortune.house)}` : null,
    result.technical_summary?.chart_data?.traditional_context?.spirit ? `Spirit: ${result.technical_summary.chart_data.traditional_context.spirit.sign} ${formatHouseRef(result.technical_summary.chart_data.traditional_context.spirit.house)}` : null,
  ].filter((value): value is string => Boolean(value));

  const summaryHero = (
    <View style={styles.heroCard}>
      <Text style={styles.eyebrow}>{result.chart_type === 'synastry' ? 'Relationship Reading' : 'Reading'}</Text>
      <Text style={styles.title}>Your year</Text>
      <Text style={styles.summaryLead}>{openingSummary.title}</Text>
      {openingSummary.paragraphs.map((paragraph, index) => (
        <GlossaryText key={`${index}-${paragraph.slice(0, 24)}`} text={paragraph} textStyle={styles.body} />
      ))}
      {openingSummary.testimony ? <Text style={styles.oracle}>{openingSummary.testimony}</Text> : null}
      {result.reading.oracle ? <Text style={styles.supporting}>{result.reading.oracle}</Text> : null}
    </View>
  );

  const chartMapCard = (
    <SurfaceCard title="Visual chart map" subtitle="The outer ring shows the natal chart. The inner ring shows the timing or live overlay. The center lines show major aspects.">
      <Text style={styles.chartHelper}>Use the chart to orient yourself first, then move through the reading in order.</Text>
      <ChartWheel
        title={result.chart_type === 'synastry' ? 'Relationship chart map' : 'Birth chart map'}
        primaryChart={result.chart_type === 'synastry' ? result.technical_summary?.primary_chart_data : result.technical_summary?.chart_data}
        secondaryChart={result.chart_type === 'synastry' ? result.technical_summary?.secondary_chart_data : result.technical_summary?.transit_chart_data}
        compact
      />
      <SecondaryButton label="Open full chart details" onPress={onOpenTechnical} icon={<MaterialCommunityIcons name="chart-bubble" size={17} color={palette.ink} />} />
    </SurfaceCard>
  );

  return (
    <>
      {activeTab === 'reading' ? chartMapCard : null}

      <View style={styles.tabWrap}>
        <Pressable style={[styles.tabPill, activeTab === 'reading' && styles.tabPillActive]} onPress={() => setActiveTab('reading')}>
          <Text style={[styles.tabText, activeTab === 'reading' && styles.tabTextActive]}>Reading</Text>
        </Pressable>
        <Pressable style={[styles.tabPill, activeTab === 'guide' && styles.tabPillActive]} onPress={() => setActiveTab('guide')}>
          <Text style={[styles.tabText, activeTab === 'guide' && styles.tabTextActive]}>Guide</Text>
        </Pressable>
      </View>

      {activeTab === 'reading' ? (
        <>

          <Text style={styles.termHint}>Tap underlined terms for quick definitions.</Text>

          {summaryHero}

          {annualBlock ? (
            <SurfaceCard title="Why this year has this theme" subtitle="Annual timing and emphasis.">
              <GlossaryText text={annualBlock.plain_meaning || annualBlock.summary} textStyle={styles.body} />
              {annualBlock.why_this_matters ? <GlossaryText text={annualBlock.why_this_matters} textStyle={styles.whyLine} /> : null}
              {annualBlock.traditional_doctrine ? <GlossaryText text={annualBlock.traditional_doctrine} textStyle={styles.supporting} /> : null}
            </SurfaceCard>
          ) : null}

          {yearMapBlock ? (
            <SurfaceCard title="The planet carrying the year" subtitle="The main planet shaping the year.">
              <GlossaryText text={yearMapBlock.plain_meaning || yearMapBlock.summary} textStyle={styles.body} />
              {yearMapBlock.why_this_matters ? <GlossaryText text={yearMapBlock.why_this_matters} textStyle={styles.whyLine} /> : null}
            </SurfaceCard>
          ) : null}

          {fortuneBlock ? (
            <SurfaceCard title="What happens to you vs. what you choose" subtitle="Fortune shows circumstance. Spirit shows chosen direction.">
              <GlossaryText text={fortuneBlock.plain_meaning || fortuneBlock.summary} textStyle={styles.body} />
              {fortuneBlock.why_this_matters ? <GlossaryText text={fortuneBlock.why_this_matters} textStyle={styles.whyLine} /> : null}
            </SurfaceCard>
          ) : null}

          {(strongest || strained) ? (
            <SurfaceCard title="Where the chart gives support and where it asks for care" subtitle="The chart does not treat every life area equally.">
              {strongest ? (
                <View style={styles.supportBlock}>
                  <Text style={styles.sectionLabel}>Most supported</Text>
                  <Text style={styles.cardTitle}>{strongest.title}</Text>
                  <GlossaryText text={topicSummary(strongest) || ''} textStyle={styles.body} />
                  {confidenceExplainer(strongest) ? <GlossaryText text={confidenceExplainer(strongest) || ''} textStyle={styles.supporting} /> : null}
                </View>
              ) : null}
              {strained ? (
                <View style={styles.supportBlock}>
                  <Text style={styles.sectionLabel}>Most strained</Text>
                  <Text style={styles.cardTitle}>{strained.title}</Text>
                  <GlossaryText text={topicSummary(strained) || ''} textStyle={styles.body} />
                  {confidenceExplainer(strained) ? <GlossaryText text={confidenceExplainer(strained) || ''} textStyle={styles.supporting} /> : null}
                </View>
              ) : null}
            </SurfaceCard>
          ) : null}

          {transitContacts.length ? (
            <SurfaceCard title="What the sky is emphasizing right now" subtitle="Today’s transits describe the weather, not the whole reading.">
              {transitStamp ? <Text style={styles.transitStamp}>{transitStamp}</Text> : null}
              <View style={styles.flowStack}>
                {skyNarrative.map((paragraph, index) => (
                  <GlossaryText key={`${index}-${paragraph.slice(0, 20)}`} text={paragraph} textStyle={styles.body} />
                ))}
              </View>
              <View style={styles.contactList}>
                {transitContacts.slice(0, 3).map((contact) => (
                  <Text key={formatTransitContact(result, contact)} style={styles.contactLine}>• {formatTransitContact(result, contact)}</Text>
                ))}
              </View>
            </SurfaceCard>
          ) : null}

          <SurfaceCard title="Reading details" subtitle="Open any card for the supporting doctrine and evidence.">
            {blocks.map((block) => (
              <InterpretationCard key={`${block.block_type}-${block.repeat_key || block.title}`} block={block} onPress={() => onOpenDetail(block)} />
            ))}
          </SurfaceCard>

          <CollapsibleCard title="How this reading was calculated" subtitle="Technical evidence and doctrine stay here so the main reading can stay readable.">
            <View style={styles.flowStack}>
              {technicalLines.map((line) => <Text key={line} style={styles.flowText}>• {line}</Text>)}
            </View>
            {solarReturnBlock?.chart_evidence?.length ? (
              <View style={styles.drawerSection}>
                <Text style={styles.sectionLabel}>Solar return</Text>
                {solarReturnBlock.chart_evidence.map((line) => <Text key={line} style={styles.flowText}>• {line}</Text>)}
              </View>
            ) : null}
            {topicBlocks.length ? (
              <View style={styles.drawerSection}>
                <Text style={styles.sectionLabel}>Confidence rules</Text>
                {topicBlocks.slice(0, 3).map((block) => (
                  <Text key={block.title} style={styles.flowText}>• {block.title}: {block.confidence_explainer || 'Traditional repeated testimony determines the confidence language.'}</Text>
                ))}
              </View>
            ) : null}
            {result.source_lenses?.length ? (
              <View style={styles.drawerSection}>
                <Text style={styles.sectionLabel}>Source notes</Text>
                {result.source_lenses.map((lens) => (
                  <Text key={lens.lens} style={styles.flowText}>• {lens.labels.join(' • ')}</Text>
                ))}
              </View>
            ) : null}
            {result.notes.length ? (
              <View style={styles.drawerSection}>
                <Text style={styles.sectionLabel}>Calculation notes</Text>
                {result.notes.map((note) => <Text key={note} style={styles.flowText}>• {note}</Text>)}
              </View>
            ) : null}
          </CollapsibleCard>

          <View style={styles.row}>
            <View style={styles.flex}><SecondaryButton label="Edit birth details" onPress={onEditOnboarding} icon={<Feather name="edit-3" size={15} color={palette.ink} />} /></View>
            <View style={styles.flex}><PrimaryButton label="Refresh reading" onPress={onRefresh} loading={loading} icon={<Feather name="refresh-cw" size={15} color={palette.white} />} /></View>
          </View>
          <SecondaryButton label="Account and settings" onPress={onOpenAccount} icon={<Ionicons name="person-circle-outline" size={17} color={palette.ink} />} />
        </>
      ) : (
        <>
          {summaryHero}

          <SurfaceCard title="How to read this page" subtitle="Move through the reading one section at a time.">
            <View style={styles.flowStack}>
              {readingFlow.map((step, index) => (
                <Text key={step} style={styles.flowText}><Text style={styles.flowIndex}>{index + 1}. </Text>{step}</Text>
              ))}
            </View>
          </SurfaceCard>

          <SurfaceCard title="Reading details" subtitle="Each concept expands into traditional doctrine and evidence.">
            <View style={styles.glossaryWrap}>
              {guideCards.map((block) => (
                <View key={block.title} style={styles.glossaryCard}>
                  <Text style={styles.glossaryTerm}>{block.title}</Text>
                  <GlossaryText text={block.plain_meaning || block.summary} textStyle={styles.glossaryMeaning} />
                  {block.traditional_doctrine ? <GlossaryText text={block.traditional_doctrine} textStyle={styles.supporting} /> : null}
                </View>
              ))}
            </View>
          </SurfaceCard>

          <SurfaceCard title="Quick term guide" subtitle="Traditional vocabulary should teach, not block understanding.">
            <View style={styles.glossaryWrap}>
              {GLOSSARY_ENTRIES.map((item) => (
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
      )}
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
  summaryLead: { fontSize: 20, lineHeight: 28, color: palette.ink, fontWeight: '700' },
  oracle: { fontSize: 14, lineHeight: 22, color: palette.ink, fontWeight: '700' },
  body: { fontSize: 15, lineHeight: 24, color: palette.ink },
  supporting: { fontSize: 13, lineHeight: 21, color: palette.muted },
  whyLine: { fontSize: 14, lineHeight: 22, color: palette.ink, fontWeight: '700' },
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
  termHint: { fontSize: 12, lineHeight: 18, color: palette.muted, fontWeight: '600' },
  supportBlock: { gap: 8, paddingTop: 4 },
  sectionLabel: { fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase', color: palette.muted, fontWeight: '700' },
  cardTitle: { fontSize: 18, lineHeight: 24, color: palette.ink, fontWeight: '700' },
  transitStamp: { fontSize: 11, lineHeight: 17, color: palette.muted, fontWeight: '700' },
  contactList: { gap: 6 },
  contactLine: { fontSize: 12, lineHeight: 18, color: palette.muted },
  chartHelper: { fontSize: 14, lineHeight: 21, color: palette.muted },
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
  collapseToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  collapseToggleText: { fontSize: 13, lineHeight: 18, color: palette.ink, fontWeight: '700' },
  drawerSection: { gap: 8, paddingTop: 8 },
  row: { flexDirection: 'row', gap: 10 },
  flex: { flex: 1 },
});
