import React, { useMemo, useState } from 'react';
import { StyleProp, StyleSheet, Text, TextStyle, View } from 'react-native';
import { glossaryDefinition } from '../utils/reading';
import { palette } from '../constants/theme';

type Segment = {
  text: string;
  term?: string;
};

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function buildSegments(value: string, terms: string[]): Segment[] {
  const usableTerms = [...terms].sort((a, b) => b.length - a.length);
  if (!usableTerms.length) return [{ text: value }];
  const pattern = new RegExp(`\\b(${usableTerms.map(escapeRegex).join('|')})\\b`, 'gi');
  const segments: Segment[] = [];
  let lastIndex = 0;

  value.replace(pattern, (match, _capture, offset: number) => {
    if (offset > lastIndex) {
      segments.push({ text: value.slice(lastIndex, offset) });
    }
    segments.push({ text: match, term: match });
    lastIndex = offset + match.length;
    return match;
  });

  if (lastIndex < value.length) {
    segments.push({ text: value.slice(lastIndex) });
  }

  return segments.length ? segments : [{ text: value }];
}

export function GlossaryText({
  text,
  textStyle,
}: {
  text: string;
  textStyle?: StyleProp<TextStyle>;
}) {
  const [activeTerm, setActiveTerm] = useState<string | null>(null);
  const matchedTerms = useMemo(() => {
    const knownTerms = [
      'Annual profection',
      'Lord of the year',
      'Contrary to sect',
      'Triplicity dignity',
      'Mixed testimony',
      'Bonification',
      'Maltreatment',
      'Succedent',
      'Angular',
      'Cadent',
      'In sect',
      'Fortune',
      'Spirit',
      'Sect',
    ];
    return knownTerms.filter((term) => new RegExp(`\\b${escapeRegex(term)}\\b`, 'i').test(text));
  }, [text]);
  const segments = useMemo(() => buildSegments(text, matchedTerms), [matchedTerms, text]);
  const definition = activeTerm ? glossaryDefinition(activeTerm) : null;

  return (
    <View style={styles.wrap}>
      <Text style={textStyle}>
        {segments.map((segment, index) => (
          segment.term ? (
            <Text
              key={`${segment.term}-${index}`}
              style={[textStyle, styles.term]}
              onPress={() => setActiveTerm((current) => (
                current?.toLowerCase() === segment.term?.toLowerCase() ? null : segment.term || null
              ))}
            >
              {segment.text}
            </Text>
          ) : (
            <React.Fragment key={`${segment.text.slice(0, 16)}-${index}`}>{segment.text}</React.Fragment>
          )
        ))}
      </Text>
      {definition && activeTerm ? (
        <View style={styles.definitionCard}>
          <Text style={styles.definitionTerm}>{activeTerm}</Text>
          <Text style={styles.definitionText}>{definition}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 8 },
  term: {
    textDecorationLine: 'underline',
    textDecorationColor: palette.accent,
    color: palette.ink,
    fontWeight: '600',
  },
  definitionCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surfaceStrong,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 4,
  },
  definitionTerm: {
    fontSize: 12,
    lineHeight: 16,
    color: palette.ink,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  definitionText: {
    fontSize: 13,
    lineHeight: 19,
    color: palette.muted,
  },
});
