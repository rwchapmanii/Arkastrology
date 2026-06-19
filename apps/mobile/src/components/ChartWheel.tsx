import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { palette } from '../constants/theme';
import { AspectRecord, NatalTechnicalChart } from '../types/app';
import { SIGN_GLYPHS, aspectColor, planetGlyph } from '../utils/chart';

function polarToCartesian(angleDegrees: number, radius: number) {
  const radians = ((angleDegrees - 90) * Math.PI) / 180;
  return {
    x: Math.cos(radians) * radius,
    y: Math.sin(radians) * radius,
  };
}

function angleLineStyle(center: number, angleDegrees: number, length: number) {
  return {
    left: center,
    top: center,
    width: length,
    transform: [{ translateY: -0.5 }, { rotate: `${angleDegrees - 90}deg` }],
  } as const;
}

function aspectLineStyle(
  size: number,
  firstLongitude: number,
  secondLongitude: number,
  radius: number,
) {
  const center = size / 2;
  const first = polarToCartesian(firstLongitude, radius);
  const second = polarToCartesian(secondLongitude, radius);
  const dx = second.x - first.x;
  const dy = second.y - first.y;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;

  return {
    left: center + first.x,
    top: center + first.y,
    width: length,
    transform: [{ translateY: -0.75 }, { rotate: `${angle}deg` }],
  } as const;
}

function findLongitude(chart: NatalTechnicalChart, id: string) {
  return chart.planets.find((planet) => planet.id === id)?.longitude;
}

function visibleAspects(chart: NatalTechnicalChart, override?: AspectRecord[]): AspectRecord[] {
  const source = override ?? chart.aspects;
  return [...source].sort((a, b) => a.orb - b.orb).slice(0, 8);
}

export function ChartWheel({
  title,
  primaryChart,
  secondaryChart,
  compact = false,
  size,
  visibleAspectRecords,
}: {
  title: string;
  primaryChart?: NatalTechnicalChart;
  secondaryChart?: NatalTechnicalChart;
  compact?: boolean;
  size?: number;
  visibleAspectRecords?: AspectRecord[];
}) {
  const baseSize = compact ? 286 : 332;
  const chartSize = size ?? baseSize;
  const scale = chartSize / baseSize;
  const center = chartSize / 2;
  const outerPlanetRadius = (compact ? 106 : 126) * scale;
  const innerPlanetRadius = (compact ? 74 : 92) * scale;
  const aspectRadius = (compact ? 63 : 82) * scale;
  const middleInset = (compact ? 20 : 20) * scale;
  const innerInset = (compact ? 56 : 56) * scale;
  const signRadius = (compact ? 128 : 148) * scale;
  const segmentLength = (compact ? 141 : 164) * scale;
  const angleRadius = (compact ? 122 : 142) * scale;
  const primaryBubbleSize = 26 * scale;
  const secondaryBubbleSize = 22 * scale;
  const primaryBubbleOffset = primaryBubbleSize / 2;
  const secondaryBubbleOffset = secondaryBubbleSize / 2;
  const primaryFontSize = 13 * scale;
  const secondaryFontSize = 11 * scale;
  const angleBadgeOffsetX = 16 * scale;
  const angleBadgeOffsetY = 10 * scale;
  const angleTextSize = 9 * scale;
  const signOffsetX = 8 * scale;
  const signOffsetY = 10 * scale;
  const signFontSize = 17 * scale;
  const centerLabelWidth = (compact ? 116 : 128) * scale;
  const centerTranslateX = (compact ? -58 : -64) * scale;
  const centerTranslateY = (compact ? -30 : -32) * scale;
  const centerLabelFontSize = 11 * scale;
  const centerValueFontSize = 15 * scale;
  const centerSubvalueFontSize = 12 * scale;

  if (!primaryChart) return null;

  const aspectLines = visibleAspects(primaryChart, visibleAspectRecords)
    .map((aspect) => {
      const firstLongitude = findLongitude(primaryChart, aspect.first);
      const secondLongitude = findLongitude(primaryChart, aspect.second);
      if (typeof firstLongitude !== 'number' || typeof secondLongitude !== 'number') return null;
      return { aspect, style: aspectLineStyle(size, firstLongitude, secondLongitude, aspectRadius) };
    })
    .filter((item): item is { aspect: AspectRecord; style: ReturnType<typeof aspectLineStyle> } => Boolean(item));

  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>{title}</Text>
      <View style={[styles.wheel, { width: chartSize, height: chartSize, borderRadius: chartSize / 2 }]}>
        <View style={[styles.middleRing, { width: chartSize - (middleInset * 2), height: chartSize - (middleInset * 2), borderRadius: (chartSize - (middleInset * 2)) / 2, left: middleInset, top: middleInset }]} />
        <View style={[styles.innerRing, { width: chartSize - (innerInset * 2), height: chartSize - (innerInset * 2), borderRadius: (chartSize - (innerInset * 2)) / 2, left: innerInset, top: innerInset }]} />

        {Array.from({ length: 12 }).map((_, index) => {
          const angle = index * 30;
          const signPos = polarToCartesian(angle + 15, signRadius);
          return (
            <React.Fragment key={`segment-${index}`}>
              <View style={[styles.segmentLine, angleLineStyle(center, angle, segmentLength)]} />
              <Text style={[styles.sign, { left: center + signPos.x - signOffsetX, top: center + signPos.y - signOffsetY, fontSize: signFontSize }]}>{SIGN_GLYPHS[index]}</Text>
            </React.Fragment>
          );
        })}

        {primaryChart.angles.map((angle) => {
          const pos = polarToCartesian(angle.longitude, angleRadius);
          return (
            <View key={`angle-${angle.id}`} style={[styles.angleBadge, { left: center + pos.x - angleBadgeOffsetX, top: center + pos.y - angleBadgeOffsetY, paddingHorizontal: 5 * scale, paddingVertical: 2 * scale }]}>
              <Text style={[styles.angleText, { fontSize: angleTextSize }]}>{planetGlyph(angle.id)}</Text>
            </View>
          );
        })}

        {aspectLines.map(({ aspect, style }, index) => (
          <View key={`${aspect.first}-${aspect.second}-${index}`} style={[styles.aspectLine, style, { backgroundColor: aspectColor(aspect.type), opacity: compact ? 0.35 : 0.48 }]} />
        ))}

        {primaryChart.planets.map((planet) => {
          const pos = polarToCartesian(planet.longitude, outerPlanetRadius);
          return (
            <View key={`primary-${planet.id}`} style={[styles.planetBubblePrimary, { width: primaryBubbleSize, height: primaryBubbleSize, borderRadius: primaryBubbleSize / 2, left: center + pos.x - primaryBubbleOffset, top: center + pos.y - primaryBubbleOffset }]}>
              <Text style={[styles.planetTextPrimary, { fontSize: primaryFontSize }]}>{planetGlyph(planet.id)}</Text>
            </View>
          );
        })}

        {secondaryChart?.planets.map((planet) => {
          const pos = polarToCartesian(planet.longitude, innerPlanetRadius);
          return (
            <View key={`secondary-${planet.id}`} style={[styles.planetBubbleSecondary, { width: secondaryBubbleSize, height: secondaryBubbleSize, borderRadius: secondaryBubbleSize / 2, left: center + pos.x - secondaryBubbleOffset, top: center + pos.y - secondaryBubbleOffset }]}>
              <Text style={[styles.planetTextSecondary, { fontSize: secondaryFontSize }]}>{planetGlyph(planet.id)}</Text>
            </View>
          );
        })}

        <View style={[styles.centerLabelWrap, { width: centerLabelWidth, transform: [{ translateX: centerTranslateX }, { translateY: centerTranslateY }] }]}>
          <Text style={[styles.centerLabel, { fontSize: centerLabelFontSize }]}>{primaryChart.house_system}</Text>
          <Text style={[styles.centerValue, { fontSize: centerValueFontSize }]}>{secondaryChart ? 'A / B overlay' : 'Aspect web'}</Text>
          <Text style={[styles.centerSubvalue, { fontSize: centerSubvalueFontSize }]}>{primaryChart.planets.length} planets • {(visibleAspectRecords ?? primaryChart.aspects).length} aspects</Text>
        </View>
      </View>
      <View style={styles.legendRow}>
        <Text style={styles.legendText}>● Outer ring = primary chart</Text>
        {secondaryChart ? <Text style={styles.legendText}>● Inner ring = secondary chart</Text> : null}
        <Text style={styles.legendText}>● Center lines = closest major aspects</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: 12 },
  title: { fontSize: 17, fontWeight: '700', color: palette.ink, letterSpacing: 0.2 },
  wheel: {
    borderWidth: 1,
    borderColor: palette.borderStrong,
    backgroundColor: palette.surface,
    position: 'relative',
    overflow: 'hidden',
  },
  middleRing: {
    position: 'absolute',
    borderWidth: 1,
    borderColor: palette.borderStrong,
    backgroundColor: palette.surfaceStrong,
  },
  innerRing: {
    position: 'absolute',
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surface,
  },
  segmentLine: {
    position: 'absolute',
    height: 1,
    backgroundColor: palette.border,
    transformOrigin: 'left center',
  },
  aspectLine: {
    position: 'absolute',
    height: 1.5,
    transformOrigin: 'left center',
  },
  sign: {
    position: 'absolute',
    fontSize: 17,
    color: palette.ink,
    fontWeight: '700',
  },
  angleBadge: {
    position: 'absolute',
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 999,
    backgroundColor: palette.surface,
    borderWidth: 1,
    borderColor: palette.borderStrong,
  },
  angleText: { fontSize: 9, color: palette.ink, fontWeight: '800' },
  planetBubblePrimary: {
    position: 'absolute',
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: palette.ink,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: palette.ink,
  },
  planetTextPrimary: { color: palette.white, fontSize: 13, fontWeight: '700' },
  planetBubbleSecondary: {
    position: 'absolute',
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: palette.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: palette.borderStrong,
  },
  planetTextSecondary: { color: palette.ink, fontSize: 11, fontWeight: '700' },
  centerLabelWrap: {
    position: 'absolute',
    left: '50%',
    top: '50%',
    alignItems: 'center',
    gap: 2,
  },
  centerLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.1, color: palette.muted, fontWeight: '700', textAlign: 'center' },
  centerValue: { fontSize: 15, color: palette.ink, fontWeight: '700', textAlign: 'center' },
  centerSubvalue: { fontSize: 12, color: palette.muted, textAlign: 'center' },
  legendRow: { gap: 4, alignItems: 'center' },
  legendText: { fontSize: 12, lineHeight: 17, color: palette.muted, textAlign: 'center' },
});
