import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { palette } from '../constants/theme';
import { InterpretationBlock } from '../types/app';
import { renderBlockIcon } from './common';

function confidenceLabel(block: InterpretationBlock) {
  if (!block.confidence) return null;
  return `${block.confidence.charAt(0).toUpperCase()}${block.confidence.slice(1)} confidence`;
}

export function InterpretationCard({ block, onPress }: { block: InterpretationBlock; onPress: () => void }) {
  const preview = block.plain_meaning || block.summary;
  const supportingLine = block.life_translation;

  return (
    <Pressable style={({ pressed }) => [styles.card, pressed && styles.cardPressed]} onPress={onPress}>
      <View style={styles.topRow}>
        <View style={styles.iconWrap}>{renderBlockIcon(block.block_type, 18)}</View>
        <View style={styles.textWrap}>
          <Text style={styles.title}>{block.title}</Text>
          {block.confidence ? <Text style={styles.confidence}>{confidenceLabel(block)}</Text> : null}
          <Text style={styles.preview} numberOfLines={3}>{preview}</Text>
          {supportingLine ? <Text style={styles.why} numberOfLines={2}>{supportingLine}</Text> : null}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: palette.surface,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: palette.border,
    padding: 18,
    gap: 12,
  },
  cardPressed: { opacity: 0.86 },
  topRow: { flexDirection: 'row', gap: 14, alignItems: 'flex-start' },
  iconWrap: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: palette.surfaceStrong,
    borderWidth: 1,
    borderColor: palette.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textWrap: { flex: 1, gap: 5 },
  title: { fontSize: 18, lineHeight: 24, color: palette.ink, fontWeight: '700' },
  confidence: { fontSize: 11, lineHeight: 15, color: palette.success, fontWeight: '700' },
  preview: { fontSize: 14, lineHeight: 21, color: palette.muted },
  why: { fontSize: 12, lineHeight: 18, color: palette.ink, fontWeight: '600' },
});
