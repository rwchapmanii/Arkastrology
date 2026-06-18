import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import React, { useMemo, useRef, useState } from 'react';
import { Animated, PanResponder, Pressable, StyleSheet, Text, View } from 'react-native';
import { ChartWheel } from '../components/ChartWheel';
import { MetricChip, SecondaryButton, SurfaceCard } from '../components/common';
import { palette } from '../constants/theme';
import { AnnualProfectionRecord, AnyReadingResponse, AspectRecord, NatalTechnicalChart, SolarReturnRecord, SynastryAspectRecord, TopicJudgmentRecord, TransitAspectRecord, YearMapRecord } from '../types/app';
import { TECHNICAL_ASPECT_TYPES, aspectColor, formatAspect, formatDegree, formatPlanetSummary, planetGlyph, signGlyph } from '../utils/chart';

function formatTransitAspect(aspect: TransitAspectRecord) {
  const timingBits = [aspect.phase, aspect.exact_at ? `exact ${aspect.exact_at.slice(0, 16).replace('T', ' ')}` : null].filter(Boolean).join(' • ');
  const owner = aspect.natal_owner === 'primary' ? 'Person A' : aspect.natal_owner === 'secondary' ? 'Person B' : null;
  return `${owner ? `${owner} • ` : ''}${planetGlyph(aspect.transit_body)} ${aspect.type} ${planetGlyph(aspect.natal_body)} • ${signGlyph(aspect.transit_sign)} ${aspect.transit_sign} to ${signGlyph(aspect.natal_sign)} ${aspect.natal_sign} • distance from exact ${aspect.orb.toFixed(1)}°${timingBits ? ` • ${timingBits}` : ''}`;
}

function prettyText(value: string | null | undefined, fallback = 'Unknown') {
  if (!value) return fallback;
  return value.replace(/_/g, ' ');
}

function formatHouseRef(house?: string | null) {
  if (!house) return 'unknown house';
  return `House ${house.replace('House', '')}`;
}

function formatLotLine(name: string, sign: string, house?: string | null, ruler?: string | null, rulerStrength?: string | null) {
  return `${name}: ${signGlyph(sign)} ${sign} • ${formatHouseRef(house)} • ruled by ${ruler ?? 'unknown'} (${prettyText(rulerStrength, 'mixed')})`;
}

function SolarReturnCard({ title, solarReturn }: { title: string; solarReturn?: SolarReturnRecord | null }) {
  if (!solarReturn) return null;

  return (
    <SurfaceCard title={title} subtitle="This is the yearly return overlay that concentrates the current profection year.">
      <Text style={styles.dataValue}>Solar year: {solarReturn.solar_year}</Text>
      {solarReturn.return_timestamp ? (
        <Text style={styles.dataValue}>
          Return moment: {solarReturn.return_timestamp.slice(0, 16).replace('T', ' ')}{solarReturn.return_timezone ? ` • ${solarReturn.return_timezone}` : ''}
        </Text>
      ) : null}
      <Text style={styles.dataValue}>
        Return Asc: {signGlyph(solarReturn.return_ascendant_sign ?? '')} {solarReturn.return_ascendant_sign} {solarReturn.return_ascendant_degree != null ? formatDegree(solarReturn.return_ascendant_degree) : ''}
      </Text>
      <Text style={styles.dataValue}>
        Return MC: {signGlyph(solarReturn.return_midheaven_sign ?? '')} {solarReturn.return_midheaven_sign} {solarReturn.return_midheaven_degree != null ? formatDegree(solarReturn.return_midheaven_degree) : ''}
      </Text>
      <Text style={styles.dataValue}>
        Sun house: {formatHouseRef(solarReturn.sun_house)} • year lord {solarReturn.year_lord ?? 'unknown'} in {formatHouseRef(solarReturn.year_lord_house)} • {prettyText(solarReturn.year_lord_strength, 'mixed')}
      </Text>
      <Text style={styles.dataValue}>
        Angular planets: {solarReturn.angular_planets.length ? solarReturn.angular_planets.map((planet) => `${planetGlyph(planet)} ${planet}`).join(', ') : 'none emphasized'}
      </Text>
      <Text style={styles.muted}>Location basis: {prettyText(solarReturn.location_status, 'unknown')}</Text>
    </SurfaceCard>
  );
}

function YearMapCard({ yearMap }: { yearMap?: YearMapRecord | null }) {
  if (!yearMap) return null;

  return (
    <SurfaceCard title="Current year map" subtitle="This merges profection timing, solar return emphasis, and the Fortune/Spirit split into one operational view.">
      {yearMap.profection_window ? <Text style={styles.dataValue}>Window: {yearMap.profection_window}</Text> : null}
      {yearMap.activated_house_title ? <Text style={styles.dataValue}>Activated house: {yearMap.activated_house_title} • {yearMap.activated_topics.join(', ') || 'topics not specified'}</Text> : null}
      {yearMap.lord_of_year ? <Text style={styles.dataValue}>Lord of the year: {yearMap.lord_of_year} • {yearMap.lord_of_year_condition ?? 'mixed'} • {formatHouseRef(yearMap.lord_of_year_house)}</Text> : null}
      {yearMap.solar_return_ascendant ? <Text style={styles.dataValue}>Solar return: {yearMap.solar_return_ascendant} rising • Sun in {formatHouseRef(yearMap.solar_return_sun_house)} • year lord in {formatHouseRef(yearMap.solar_return_year_lord_house)}</Text> : null}
      {yearMap.fortune_emphasis ? <Text style={styles.dataValue}>{yearMap.fortune_emphasis}</Text> : null}
      {yearMap.spirit_emphasis ? <Text style={styles.dataValue}>{yearMap.spirit_emphasis}</Text> : null}
      {yearMap.fortune_spirit_alignment ? <Text style={styles.dataValue}>Fortune/Spirit alignment: {prettyText(yearMap.fortune_spirit_alignment)}</Text> : null}
      {yearMap.guidance ? <Text style={styles.muted}>{yearMap.guidance}</Text> : null}
    </SurfaceCard>
  );
}

function TopicJudgmentCard({ topicJudgments, mode }: { topicJudgments: TopicJudgmentRecord[]; mode: 'natal' | 'synastry' }) {
  if (!topicJudgments.length) return null;

  return (
    <SurfaceCard
      title={mode === 'synastry' ? 'Relationship topic judgments' : 'Topic judgments'}
      subtitle={
        mode === 'synastry'
          ? 'These topics combine each person’s natal readiness with ruler contacts, helper planets, and current-year activation.'
          : 'Each topic is scored by repeated testimony, with an explicit evidence trail behind the prose layer.'
      }
    >
      <View style={styles.subsection}>
        {topicJudgments.map((topic) => (
          <View key={topic.key} style={styles.topicCard}>
            <Text style={styles.topicTitle}>{topic.title}</Text>
            <Text style={styles.dataValue}>Classification: {prettyText(topic.classification)} • confidence: {topic.confidence} • score: {topic.score}</Text>
            <Text style={styles.dataValue}>Houses: {topic.relevant_houses.map((house) => `H${house}`).join(', ')}{topic.relevant_lot ? ` • lot: ${topic.relevant_lot}` : ''}</Text>
            {topic.evidence_items.slice(0, 3).map((item, index) => (
              <Text key={`${topic.key}-evidence-${index}`} style={styles.muted}>
                {index + 1}. {item.observation} {item.interpretation}
              </Text>
            ))}
          </View>
        ))}
      </View>
    </SurfaceCard>
  );
}

function TraditionalFrameCard({
  title,
  chart,
  annualProfection,
}: {
  title: string;
  chart?: NatalTechnicalChart;
  annualProfection?: AnnualProfectionRecord | null;
}) {
  const context = chart?.traditional_context;
  if (!context) return null;

  return (
    <SurfaceCard title={title} subtitle="This is the traditional frame the reading now uses before it makes topical claims.">
      <View style={styles.sectionGroup}>
        <Text style={styles.dataValue}>
          {prettyText(context.sect)} chart • sect light {context.sect_light} • {signGlyph(context.ascendant_sign ?? '')} {context.ascendant_sign} rising
        </Text>
        <Text style={styles.dataValue}>
          Ascendant ruler: {context.ascendant_ruler} in {context.ascendant_ruler_sign ?? 'unknown sign'} • {formatHouseRef(context.ascendant_ruler_house)} • {prettyText(context.ascendant_ruler_strength, 'mixed')}
        </Text>
      </View>

      <View style={styles.subsection}>
        <Text style={styles.subsectionTitle}>Fortune and Spirit</Text>
        {context.fortune ? <Text style={styles.dataValue}>{formatLotLine('Fortune', context.fortune.sign, context.fortune.house, context.fortune.ruler, context.fortune.ruler_strength)}</Text> : null}
        {context.spirit ? <Text style={styles.dataValue}>{formatLotLine('Spirit', context.spirit.sign, context.spirit.house, context.spirit.ruler, context.spirit.ruler_strength)}</Text> : null}
      </View>

      <View style={styles.subsection}>
        <Text style={styles.subsectionTitle}>House rulers</Text>
        <View style={styles.houseWrap}>
          {context.house_rulers.map((record) => (
            <View key={`${title}-ruler-${record.house_number}`} style={styles.houseChip}>
              <Text style={styles.houseText}>
                H{record.house_number} {signGlyph(record.sign)} {record.sign} → {planetGlyph(record.ruler)} {record.ruler}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {annualProfection ? (
        <View style={styles.subsection}>
          <Text style={styles.subsectionTitle}>Annual profection</Text>
          <Text style={styles.dataValue}>
            Age {annualProfection.age} • House {annualProfection.activated_house} • {signGlyph(annualProfection.activated_sign)} {annualProfection.activated_sign}
          </Text>
          <Text style={styles.dataValue}>
            Lord of the year: {planetGlyph(annualProfection.lord_of_year)} {annualProfection.lord_of_year} • {annualProfection.lord_of_year_sign ?? 'unknown sign'} • {formatHouseRef(annualProfection.lord_of_year_house)} • {prettyText(annualProfection.lord_of_year_strength, 'mixed')}
          </Text>
          {annualProfection.starts_at && annualProfection.ends_at ? (
            <Text style={styles.dataValue}>Window: {annualProfection.starts_at.slice(0, 10)} to {annualProfection.ends_at.slice(0, 10)}</Text>
          ) : null}
        </View>
      ) : null}
    </SurfaceCard>
  );
}

function ChartDataCard({ title, chart, aspectsTitle, aspects }: { title: string; chart?: NatalTechnicalChart; aspectsTitle: string; aspects: Array<AspectRecord | SynastryAspectRecord> }) {
  if (!chart) return null;

  return (
    <SurfaceCard title={title} subtitle="This is the detailed chart data behind the reading.">
      <View style={styles.sectionGroup}>
        {chart.planets.map((planet) => (
          <View key={`${title}-${planet.id}`} style={styles.dataRow}>
            <Text style={styles.dataValue}>{formatPlanetSummary(planet)}</Text>
          </View>
        ))}
      </View>
      <View style={styles.subsection}>
        <Text style={styles.subsectionTitle}>Angles</Text>
        {chart.angles.length === 0 ? <Text style={styles.muted}>Angles are hidden in simple mode because the birth time is not exact enough.</Text> : chart.angles.map((angle) => (
          <Text key={`${title}-${angle.id}`} style={styles.dataValue}>{planetGlyph(angle.id)} {angle.id} • {signGlyph(angle.sign)} {angle.sign} {formatDegree(angle.sign_degree)}</Text>
        ))}
      </View>
      <View style={styles.subsection}>
        <Text style={styles.subsectionTitle}>House cusps</Text>
        {chart.houses.length === 0 ? <Text style={styles.muted}>House cusps are hidden in simple mode because the birth time is not exact enough.</Text> : <View style={styles.houseWrap}>
          {chart.houses.map((house) => (
            <View key={`${title}-${house.id}`} style={styles.houseChip}>
              <Text style={styles.houseText}>{house.id}: {signGlyph(house.sign)} {house.sign}</Text>
            </View>
          ))}
        </View>}
      </View>
      <View style={styles.subsection}>
        <Text style={styles.subsectionTitle}>{aspectsTitle}</Text>
        {aspects.length === 0 ? <Text style={styles.muted}>No aspects returned for the current filter.</Text> : aspects.map((aspect, index) => (
          <Text key={`${title}-${aspect.first}-${aspect.second}-${index}`} style={styles.dataValue}>{formatAspect(aspect)}</Text>
        ))}
      </View>
    </SurfaceCard>
  );
}

function AspectFilterPill({ label, active, onPress, color }: { label: string; active: boolean; onPress: () => void; color: string }) {
  return (
    <Pressable onPress={onPress} style={[styles.filterPill, active && styles.filterPillActive, { borderColor: color }] }>
      <View style={[styles.filterDot, { backgroundColor: color, opacity: active ? 1 : 0.45 }]} />
      <Text style={[styles.filterText, active && styles.filterTextActive]}>{label}</Text>
    </Pressable>
  );
}

export function TechnicalChartScreen({ result, onBack }: { result: AnyReadingResponse; onBack: () => void }) {
  const primaryChart = result.chart_type === 'synastry' ? result.technical_summary?.primary_chart_data : result.technical_summary?.chart_data;
  const secondaryChart = result.chart_type === 'synastry' ? result.technical_summary?.secondary_chart_data : undefined;
  const transitChart = result.technical_summary?.transit_chart_data;
  const solarReturnChart = result.chart_type === 'synastry' ? result.technical_summary?.primary_solar_return_chart_data : result.technical_summary?.solar_return_chart_data;
  const secondarySolarReturnChart = result.chart_type === 'synastry' ? result.technical_summary?.secondary_solar_return_chart_data : undefined;
  const interChartAspects = result.chart_type === 'synastry' ? result.technical_summary?.inter_chart_aspects || [] : [];
  const natalTransitAspects = result.technical_summary?.transit_aspects || [];
  const primaryTransitAspects = result.technical_summary?.primary_transit_aspects || [];
  const secondaryTransitAspects = result.technical_summary?.secondary_transit_aspects || [];
  const yearMap = result.chart_type === 'natal' ? result.technical_summary?.year_map : undefined;
  const topicJudgments = result.technical_summary?.topic_judgments || [];
  const transitStamp = result.technical_summary?.transit_timestamp
    ? `${result.technical_summary.transit_timestamp.slice(0, 16).replace('T', ' ')}${result.technical_summary?.transit_timezone ? ` • ${result.technical_summary.transit_timezone}` : ''}`
    : null;
  const [zoom, setZoom] = useState(1);
  const [activeAspectTypes, setActiveAspectTypes] = useState<string[]>([...TECHNICAL_ASPECT_TYPES]);
  const [showRawData, setShowRawData] = useState(false);
  const pan = useRef(new Animated.ValueXY({ x: 0, y: 0 })).current;

  const panResponder = useMemo(
    () => PanResponder.create({
      onMoveShouldSetPanResponder: (_, gestureState) => Math.abs(gestureState.dx) > 3 || Math.abs(gestureState.dy) > 3,
      onPanResponderGrant: () => {
        pan.extractOffset();
      },
      onPanResponderMove: Animated.event([null, { dx: pan.x, dy: pan.y }], { useNativeDriver: false }),
      onPanResponderRelease: () => {
        pan.flattenOffset();
      },
    }),
    [pan],
  );

  const filteredPrimaryAspects = useMemo(() => {
    return primaryChart?.aspects.filter((aspect) => activeAspectTypes.includes(aspect.type)) || [];
  }, [activeAspectTypes, primaryChart]);

  const filteredSecondaryAspects = useMemo(() => {
    return secondaryChart?.aspects.filter((aspect) => activeAspectTypes.includes(aspect.type)) || [];
  }, [activeAspectTypes, secondaryChart]);

  const filteredInterChartAspects = useMemo(() => {
    return interChartAspects.filter((aspect) => activeAspectTypes.includes(aspect.type));
  }, [activeAspectTypes, interChartAspects]);

  const metricItems = [
    { label: 'House system', value: result.technical_summary?.house_system ?? 'Whole Sign', icon: <MaterialCommunityIcons name="orbit" size={14} color={palette.muted} /> },
    { label: 'Precision', value: result.technical_summary?.precision_mode ?? result.status, icon: <Feather name="target" size={14} color={palette.muted} /> },
    { label: 'Sect', value: prettyText(primaryChart?.traditional_context?.sect, 'n/a'), icon: <MaterialCommunityIcons name="weather-sunny-alert" size={14} color={palette.muted} /> },
    {
      label: 'Year lord',
      value: result.chart_type === 'synastry'
        ? (result.technical_summary?.primary_annual_profection?.lord_of_year ?? 'n/a')
        : (result.technical_summary?.annual_profection?.lord_of_year ?? 'n/a'),
      icon: <MaterialCommunityIcons name="calendar-star" size={14} color={palette.muted} />,
    },
    { label: 'Planets', value: String(primaryChart?.planets.length ?? 0), icon: <Ionicons name="planet-outline" size={14} color={palette.muted} /> },
    { label: 'Angles', value: String(primaryChart?.angles.length ?? 0), icon: <Feather name="crosshair" size={14} color={palette.muted} /> },
    { label: 'Visible aspects', value: String(result.chart_type === 'synastry' ? filteredInterChartAspects.length : filteredPrimaryAspects.length), icon: <MaterialCommunityIcons name="vector-link" size={14} color={palette.muted} /> },
    { label: 'Topic judgments', value: String(topicJudgments.length), icon: <MaterialCommunityIcons name="notebook-outline" size={14} color={palette.muted} /> },
    { label: 'Transit hits', value: String(result.chart_type === 'synastry' ? (primaryTransitAspects.length + secondaryTransitAspects.length) : natalTransitAspects.length), icon: <Ionicons name="flash-outline" size={14} color={palette.muted} /> },
  ];

  function toggleAspectType(type: string) {
    setActiveAspectTypes((current) => {
      if (current.includes(type)) {
        const next = current.filter((item) => item !== type);
        return next.length > 0 ? next : current;
      }
      return [...current, type];
    });
  }

  function resetViewport() {
    setZoom(1);
    pan.setValue({ x: 0, y: 0 });
    pan.setOffset({ x: 0, y: 0 });
  }

  return (
    <>
      <SurfaceCard title="Chart details" subtitle="Use this screen when you want the underlying chart data, not just the plain-language interpretation." accent>
        <Text style={styles.heroTitle}>{result.chart_type === 'synastry' ? 'Relationship chart details' : 'Birth chart details'}</Text>
        <Text style={styles.heroBody}>Drag the chart to move it, zoom in for a closer look, and filter aspect types to study one pattern at a time.</Text>
        <View style={styles.metricGrid}>
          {metricItems.map((item) => (
            <MetricChip key={`${item.label}-${item.value}`} label={item.label} value={item.value} icon={item.icon} />
          ))}
        </View>
        <SecondaryButton label={showRawData ? 'Hide raw chart data' : 'Show raw chart data'} onPress={() => setShowRawData((value) => !value)} icon={<Feather name={showRawData ? 'eye-off' : 'eye'} size={15} color={palette.ink} />} />
      </SurfaceCard>

      <SurfaceCard title="Aspect filter" subtitle="Use these filters to simplify the chart lines and focus on one aspect type at a time.">
        <View style={styles.filterWrap}>
          {TECHNICAL_ASPECT_TYPES.map((type) => (
            <AspectFilterPill
              key={type}
              label={type}
              active={activeAspectTypes.includes(type)}
              color={aspectColor(type)}
              onPress={() => toggleAspectType(type)}
            />
          ))}
        </View>
      </SurfaceCard>

      <SurfaceCard title="Chart wheel" subtitle={result.chart_type === 'synastry' ? 'Drag to move the chart. Outer ring = Person A, inner ring = Person B.' : 'Drag to move and zoom. The inner ring shows the current transit layer over the birth chart.'}>
        <View style={styles.viewportControls}>
          <SecondaryButton label="Zoom out" onPress={() => setZoom((value) => Math.max(0.75, Number((value - 0.15).toFixed(2))))} icon={<Feather name="minus" size={15} color={palette.ink} />} />
          <View style={styles.zoomStatusWrap}>
            <Text style={styles.zoomLabel}>Zoom</Text>
            <Text style={styles.zoomValue}>{Math.round(zoom * 100)}%</Text>
          </View>
          <SecondaryButton label="Zoom in" onPress={() => setZoom((value) => Math.min(2.2, Number((value + 0.15).toFixed(2))))} icon={<Feather name="plus" size={15} color={palette.ink} />} />
          <SecondaryButton label="Reset view" onPress={resetViewport} icon={<Feather name="maximize-2" size={15} color={palette.ink} />} />
        </View>

        <View style={styles.viewport}>
          <Animated.View
            {...panResponder.panHandlers}
            style={{ transform: [...pan.getTranslateTransform(), { scale: zoom }] }}
          >
            <ChartWheel
              title={result.chart_type === 'synastry' ? 'Synastry wheel' : 'Natal + transit overlay'}
              primaryChart={primaryChart}
              secondaryChart={result.chart_type === 'synastry' ? secondaryChart : transitChart}
              visibleAspectRecords={filteredPrimaryAspects}
            />
          </Animated.View>
        </View>
      </SurfaceCard>

      {showRawData ? (
        <>
          <TraditionalFrameCard
            title={result.chart_type === 'synastry' ? 'Person A traditional frame' : 'Traditional frame'}
            chart={primaryChart}
            annualProfection={result.chart_type === 'synastry' ? result.technical_summary?.primary_annual_profection : result.technical_summary?.annual_profection}
          />
          <SolarReturnCard
            title={result.chart_type === 'synastry' ? 'Person A solar return' : 'Solar return overlay'}
            solarReturn={result.chart_type === 'synastry' ? result.technical_summary?.primary_solar_return : result.technical_summary?.solar_return}
          />
          {result.chart_type === 'natal' ? <YearMapCard yearMap={yearMap} /> : null}
          {secondaryChart ? (
            <>
              <TraditionalFrameCard
                title="Person B traditional frame"
                chart={secondaryChart}
                annualProfection={result.technical_summary?.secondary_annual_profection}
              />
              <SolarReturnCard
                title="Person B solar return"
                solarReturn={result.technical_summary?.secondary_solar_return}
              />
            </>
          ) : null}
          <TopicJudgmentCard topicJudgments={topicJudgments} mode={result.chart_type} />
          <ChartDataCard
            title={result.chart_type === 'synastry' ? 'Person A chart' : 'Chart placements'}
            chart={primaryChart}
            aspectsTitle="Visible major aspects"
            aspects={filteredPrimaryAspects}
          />
          {secondaryChart ? <ChartDataCard title="Person B chart" chart={secondaryChart} aspectsTitle="Visible Person B major aspects" aspects={filteredSecondaryAspects} /> : null}
          {solarReturnChart ? <ChartDataCard title={result.chart_type === 'synastry' ? 'Person A solar return chart' : 'Solar return chart'} chart={solarReturnChart} aspectsTitle="Solar return aspects" aspects={solarReturnChart.aspects.filter((aspect) => activeAspectTypes.includes(aspect.type))} /> : null}
          {secondarySolarReturnChart ? <ChartDataCard title="Person B solar return chart" chart={secondarySolarReturnChart} aspectsTitle="Solar return aspects" aspects={secondarySolarReturnChart.aspects.filter((aspect) => activeAspectTypes.includes(aspect.type))} /> : null}
          {transitChart ? <ChartDataCard title="Live transit chart" chart={transitChart} aspectsTitle="Transit chart aspects" aspects={transitChart.aspects.filter((aspect) => activeAspectTypes.includes(aspect.type))} /> : null}

          {result.chart_type === 'natal' && natalTransitAspects.length ? (
            <SurfaceCard title="Current sky contacts" subtitle={transitStamp ? `Calculated for ${transitStamp}.` : 'These are the current sky contacts against the birth chart.'}>
              {natalTransitAspects.map((aspect, index) => (
                <Text key={`${aspect.transit_body}-${aspect.natal_body}-${aspect.type}-${index}`} style={styles.dataValue}>{formatTransitAspect(aspect)}</Text>
              ))}
            </SurfaceCard>
          ) : null}

          {result.chart_type === 'synastry' ? (
            <SurfaceCard title="Relationship aspects" subtitle="These cross-chart aspects help drive the relationship reading.">
              {filteredInterChartAspects.length === 0 ? <Text style={styles.muted}>No inter-chart aspects returned for the current filter.</Text> : filteredInterChartAspects.map((aspect, index) => (
                <Text key={`${aspect.first_owner}-${aspect.first}-${aspect.second_owner}-${aspect.second}-${index}`} style={styles.dataValue}>{formatAspect(aspect)}</Text>
              ))}
            </SurfaceCard>
          ) : null}

          {result.chart_type === 'synastry' && (primaryTransitAspects.length || secondaryTransitAspects.length) ? (
            <SurfaceCard title="Shared current sky" subtitle={transitStamp ? `Calculated for ${transitStamp}.` : 'These are the current sky contacts against both birth charts.'}>
              {primaryTransitAspects.map((aspect, index) => (
                <Text key={`primary-${aspect.transit_body}-${aspect.natal_body}-${aspect.type}-${index}`} style={styles.dataValue}>{formatTransitAspect(aspect)}</Text>
              ))}
              {secondaryTransitAspects.map((aspect, index) => (
                <Text key={`secondary-${aspect.transit_body}-${aspect.natal_body}-${aspect.type}-${index}`} style={styles.dataValue}>{formatTransitAspect(aspect)}</Text>
              ))}
            </SurfaceCard>
          ) : null}
        </>
      ) : null}

      <SecondaryButton label="Back to reading" onPress={onBack} icon={<Feather name="arrow-left" size={15} color={palette.ink} />} />
    </>
  );
}

const styles = StyleSheet.create({
  heroTitle: { fontSize: 24, lineHeight: 30, fontWeight: '700', color: palette.ink },
  heroBody: { fontSize: 15, lineHeight: 22, color: palette.ink },
  metricGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  filterWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  filterPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: palette.border,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 9,
    backgroundColor: palette.surface,
  },
  filterPillActive: { backgroundColor: palette.ink, borderColor: palette.ink },
  filterDot: { width: 10, height: 10, borderRadius: 5 },
  filterText: { fontSize: 12, lineHeight: 16, color: palette.muted, fontWeight: '600', textTransform: 'capitalize' },
  filterTextActive: { color: palette.white },
  viewportControls: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, alignItems: 'center', justifyContent: 'center' },
  zoomStatusWrap: { alignItems: 'center', minWidth: 68 },
  zoomLabel: { fontSize: 11, letterSpacing: 1.1, textTransform: 'uppercase', color: palette.muted, fontWeight: '700' },
  zoomValue: { fontSize: 18, fontWeight: '700', color: palette.ink },
  viewport: {
    minHeight: 380,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surface,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sectionGroup: { gap: 10 },
  subsection: { gap: 10 },
  subsectionTitle: { fontSize: 12, letterSpacing: 1.2, textTransform: 'uppercase', color: palette.ink, fontWeight: '700' },
  topicCard: { gap: 8, padding: 16, borderRadius: 16, borderWidth: 1, borderColor: palette.border, backgroundColor: palette.surface },
  topicTitle: { fontSize: 15, lineHeight: 21, color: palette.ink, fontWeight: '700' },
  dataRow: { paddingBottom: 2 },
  dataValue: { fontSize: 14, lineHeight: 21, color: palette.ink },
  houseWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  houseChip: { borderWidth: 1, borderColor: palette.border, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 7, backgroundColor: palette.surfaceStrong },
  houseText: { fontSize: 13, color: palette.ink, fontWeight: '600' },
  muted: { fontSize: 14, lineHeight: 21, color: palette.muted },
});
