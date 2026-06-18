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
  visibleAspectRecords,
}: {
  title: string;
  primaryChart?: NatalTechnicalChart;
  secondaryChart?: NatalTechnicalChart;
  compact?: boolean;
  visibleAspectRecords?: AspectRecord[];
}) {
  const size = compact ? 286 : 332;
  const center = size / 2;
  const outerPlanetRadius = compact ? 106 : 126;
  const innerPlanetRadius = compact ? 74 : 92;
  const aspectRadius = compact ? 63 : 82;

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
      <View style={[styles.wheel, { width: size, height: size, borderRadius: size / 2 }]}>
        <View style={[styles.middleRing, { width: size - 40, height: size - 40, borderRadius: (size - 40) / 2, left: 20, top: 20 }]} />
        <View style={[styles.innerRing, { width: size - 112, height: size - 112, borderRadius: (size - 112) / 2, left: 56, top: 56 }]} />

        {Array.from({ length: 12 }).map((_, index) => {
          const angle = index * 30;
          const signPos = polarToCartesian(angle + 15, compact ? 128 : 148);
          return (
            <React.Fragment key={`segment-${index}`}>
              <View style={[styles.segmentLine, angleLineStyle(center, angle, compact ? 141 : 164)]} />
              <Text style={[styles.sign, { left: center + signPos.x - 8, top: center + signPos.y - 10 }]}>{SIGN_GLYPHS[index]}</Text>
            </React.Fragment>
          );
        })}

        {primaryChart.angles.map((angle) => {
          const pos = polarToCartesian(angle.longitude, compact ? 122 : 142);
          return (
            <View key={`angle-${angle.id}`} style={[styles.angleBadge, { left: center + pos.x - 16, top: center + pos.y - 10 }]}>
              <Text style={styles.angleText}>{planetGlyph(angle.id)}</Text>
            </View>
          );
        })}

        {aspectLines.map(({ aspect, style }, index) => (
          <View key={`${aspect.first}-${aspect.second}-${index}`} style={[styles.aspectLine, style, { backgroundColor: aspectColor(aspect.type), opacity: compact ? 0.35 : 0.48 }]} />
        ))}

        {primaryChart.planets.map((planet) => {
          const pos = polarToCartesian(planet.longitude, outerPlanetRadius);
          return (
            <View key={`primary-${planet.id}`} style={[styles.planetBubblePrimary, { left: center + pos.x - 13, top: center + pos.y - 13 }]}>
              <Text style={styles.planetTextPrimary}>{planetGlyph(planet.id)}</Text>
            </View>
          );
        })}

        {secondaryChart?.planets.map((planet) => {
          const pos = polarToCartesian(planet.longitude, innerPlanetRadius);
          return (
            <View key={`secondary-${planet.id}`} style={[styles.planetBubbleSecondary, { left: center + pos.x - 11, top: center + pos.y - 11 }]}>
              <Text style={styles.planetTextSecondary}>{planetGlyph(planet.id)}</Text>
            </View>
          );
        })}

        <View style={[styles.centerLabelWrap, compact && styles.centerLabelWrapCompact]}>
          <Text style={styles.centerLabel}>{primaryChart.house_system}</Text>
          <Text style={styles.centerValue}>{secondaryChart ? 'A / B overlay' : 'Aspect web'}</Text>
          <Text style={styles.centerSubvalue}>{primaryChart.planets.length} planets • {(visibleAspectRecords ?? primaryChart.aspects).length} aspects</Text>
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
    transform: [{ translateX: -64 }, { translateY: -32 }],
    alignItems: 'center',
    width: 128,
    gap: 2,
  },
  centerLabelWrapCompact: {
    transform: [{ translateX: -58 }, { translateY: -30 }],
    width: 116,
  },
  centerLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.1, color: palette.muted, fontWeight: '700', textAlign: 'center' },
  centerValue: { fontSize: 15, color: palette.ink, fontWeight: '700', textAlign: 'center' },
  centerSubvalue: { fontSize: 12, color: palette.muted, textAlign: 'center' },
  legendRow: { gap: 4, alignItems: 'center' },
  legendText: { fontSize: 12, lineHeight: 17, color: palette.muted, textAlign: 'center' },
});
