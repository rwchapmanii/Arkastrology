import { Feather } from '@expo/vector-icons';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { GlossaryText } from '../components/GlossaryText';
import { palette } from '../constants/theme';
import { SecondaryButton, SurfaceCard, renderBlockIcon } from '../components/common';
import { glossaryDefinition } from '../utils/reading';
import { InterpretationBlock } from '../types/app';

function prettyBlockType(value: string) {
  return {
    chart_foundation: 'traditional chart foundation',
    fortune_spirit: 'Fortune and Spirit context',
    annual_profection: 'annual profection timing',
    solar_return: 'solar return overlay',
    year_map: 'current year map',
    topic_judgment: 'topical judgment from repeated testimony',
    solar_identity: 'core identity',
    lunar_pattern: 'emotional pattern',
    rising_style: 'first impression and outer style',
    ontology_signature: 'big picture chart pattern',
    levi_current: 'supplemental symbolic theme',
    house_focus: 'life area with extra emphasis',
    major_aspect: 'strong inner pattern',
    planet_emphasis: 'planetary teaching point',
    jungian_trigger: 'psychological growth pattern',
    imaginal_prompt: 'reflective prompt',
    synastry_natal_frame: "one person's natal frame in the bond",
    synastry_yearly_bridge: 'how the two current years meet',
    synastry_topic_judgment: 'relationship topic judgment from repeated testimony',
    synastry_sign_pair: 'core style match between two people',
    relationship_climate: 'relationship climate',
    synastry_aspect: 'relationship pattern',
    synastry_attraction: 'attraction pattern',
    synastry_core_bond: 'core emotional bond',
    synastry_prompt: 'relationship reflection prompt',
    transit_current: 'current live influence',
  }[value] || value.replace(/_/g, ' ');
}

function realLifeExample(block: InterpretationBlock) {
  const examples: Record<string, string> = {
    chart_foundation: 'This may look like the chart having an obvious structural center of gravity, where one planet keeps carrying the story of body, direction, and first response.',
    fortune_spirit: 'This may look like one part of life feeling circumstantial and bodily, while another part feels more intentional, chosen, or vocation-shaped.',
    annual_profection: 'This may look like one house topic becoming the year’s repeated classroom, with one planet acting like the main timer or gatekeeper.',
    solar_return: 'This may look like the year taking on a particular tone, with a few houses and planets becoming much louder until the next birthday cycle.',
    year_map: 'This may look like the year suddenly becoming much easier to track because one house, one year lord, and one circumstantial-versus-intentional split keep repeating in concrete events.',
    topic_judgment: 'This may look like a life area showing mixed or repeated testimony across house, ruler, occupants, and lots instead of hinging on one placement.',
    solar_identity: 'This may look like taking your purpose seriously, wanting your life to mean something, or feeling pulled toward visible responsibility.',
    lunar_pattern: 'This may look like certain moods returning under stress, needing comfort in a specific way, or reacting before you have words for the feeling.',
    rising_style: 'This may look like seeming reserved, intense, warm, careful, or fast-moving before people know the deeper you.',
    ontology_signature: 'This may look like the same life themes returning through work, family, relationships, or personal turning points.',
    levi_current: 'This is a supplemental symbolic or imaginal theme. It can describe the pattern well, but it does not replace the chart structure underneath it.',
    house_focus: 'This may look like one life area becoming a repeated classroom, where the same lesson keeps coming back in different forms.',
    major_aspect: 'This may look like two parts of you pulling in different directions until you learn how to hold both at once.',
    planet_emphasis: 'This may look like a specific habit, strength, or stress pattern showing up in a very recognizable way in daily life.',
    jungian_trigger: 'This may look like repeating emotional reactions, familiar conflicts, or strong projections that keep asking for reflection.',
    imaginal_prompt: 'This may look like a dream image, journal theme, or repeating symbol that keeps returning until you slow down and notice it.',
    synastry_natal_frame: 'This may look like one person entering the relationship through a very live life chapter, such as home, career, partnership, or family pressure already being active before any specific interaction happens.',
    synastry_yearly_bridge: 'This may look like the relationship feeling intense, easy, or mismatched partly because each person is carrying a different year-lord story at the same time.',
    synastry_topic_judgment: 'This may look like one part of the relationship, such as commitment, attraction, communication, home life, or shared purpose, becoming the real place where the bond succeeds or struggles.',
    synastry_sign_pair: 'This may look like two people having a recognizable style together before they even discuss deeper issues.',
    relationship_climate: 'This may look like the relationship feeling mostly easy, mostly demanding, or highly focused in a few repeating themes.',
    synastry_aspect: 'This may look like one repeated interaction pattern between two people showing up in conversations, conflict, attraction, or support.',
    synastry_attraction: 'This may look like how the relationship handles chemistry, desire, pursuit, pacing, and mutual interest.',
    synastry_core_bond: 'This may look like the way two people care for each other emotionally, or miss each other emotionally, over and over.',
    synastry_prompt: 'This may look like journaling what each person brings out emotionally, symbolically, or psychologically in the other.',
    transit_current: 'This may look like a theme suddenly feeling louder, more urgent, or more emotionally charged than usual for a while.',
  };
  return examples[block.block_type] || 'This may show up as a repeated habit, pressure point, or life theme that becomes easier to notice once you know what to look for.';
}

function confidenceSummary(block: InterpretationBlock) {
  if (block.confidence_explainer) return block.confidence_explainer;
  if (!block.confidence) return null;
  if (block.confidence === 'high') return 'High confidence means several traditional factors point in the same direction.';
  if (block.confidence === 'medium') return 'Medium confidence means several factors point this way, but the testimony is not unanimous.';
  return 'Low confidence means the chart offers a clue, but the testimony is still thin or divided.';
}

export function DetailScreen({ block, onBack }: { block: InterpretationBlock; onBack: () => void }) {
  const mainMeaning = block.plain_meaning || block.summary;
  const doctrine = block.traditional_doctrine;
  const evidenceLines = block.chart_evidence?.length ? block.chart_evidence : [];
  const useInLife = block.life_translation || realLifeExample(block);
  const confidenceText = confidenceSummary(block);

  return (
    <>
      <SurfaceCard title={block.title} subtitle={prettyBlockType(block.block_type)} accent>
        <View style={styles.heroRow}>
          <View style={styles.iconWrap}>{renderBlockIcon(block.block_type, 24)}</View>
          <View style={styles.textWrap}>
            <Text style={styles.title}>{block.title}</Text>
            <Text style={styles.subtitle}>{prettyBlockType(block.block_type)}</Text>
          </View>
        </View>
        {block.confidence ? <Text style={styles.confidence}>{block.confidence.charAt(0).toUpperCase() + block.confidence.slice(1)} confidence</Text> : null}
        <GlossaryText text={mainMeaning} textStyle={styles.summary} />
        {confidenceText ? <GlossaryText text={confidenceText} textStyle={styles.supporting} /> : null}
      </SurfaceCard>

      {doctrine ? (
        <SurfaceCard title="Traditional rule" subtitle="The doctrine underneath this reading.">
          <GlossaryText text={doctrine} textStyle={styles.summary} />
        </SurfaceCard>
      ) : null}

      {evidenceLines.length ? (
        <SurfaceCard title="Chart evidence" subtitle="These are the specific chart facts supporting this part of the reading.">
          <View style={styles.caveatStack}>
            {evidenceLines.map((line) => (
              <GlossaryText key={line} text={`• ${line}`} textStyle={styles.summary} />
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      <SurfaceCard title="What it may look like in life" subtitle="Use this as a bridge between symbolic language and everyday experience.">
        <GlossaryText text={useInLife} textStyle={styles.summary} />
      </SurfaceCard>

      {block.caveat || block.caveats.length ? (
        <SurfaceCard title="Caveat" subtitle="Traditional astrology points to emphasis and pattern, not mechanical certainty.">
          <View style={styles.caveatStack}>
            {block.caveat ? <GlossaryText text={`• ${block.caveat}`} textStyle={styles.summary} /> : null}
            {block.caveats.map((caveat) => (
              <GlossaryText key={caveat} text={`• ${caveat}`} textStyle={styles.summary} />
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      {block.evidence_items.length ? (
        <SurfaceCard title="Technical evidence" subtitle="This is the full reasoning trail behind the interpretation.">
          <View style={styles.evidenceStack}>
            {block.evidence_items.map((item, index) => (
              <View key={`${block.title}-evidence-${index}`} style={styles.evidenceCard}>
                <Text style={styles.evidenceLabel}>Observation</Text>
                <Text style={styles.evidenceText}>{item.observation}</Text>
                <Text style={styles.evidenceLabel}>Rule</Text>
                <Text style={styles.evidenceText}>{item.rule}</Text>
                <Text style={styles.evidenceLabel}>Interpretation</Text>
                <Text style={styles.evidenceText}>{item.interpretation}</Text>
                <Text style={styles.evidenceMeta}>Effect on confidence: {item.confidence_effect}</Text>
                {item.caveat ? <Text style={styles.evidenceCaveat}>Caveat: {item.caveat}</Text> : null}
              </View>
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      {block.technical_terms?.length ? (
        <SurfaceCard title="Technical terms in this card" subtitle="These are the main traditional terms behind this section.">
          <View style={styles.termCardWrap}>
            {block.technical_terms.map((term) => (
              <View key={term} style={styles.termCard}>
                <Text style={styles.termTitle}>{term}</Text>
                <Text style={styles.termMeaning}>{glossaryDefinition(term) || 'This term is part of the traditional reasoning layer behind the card.'}</Text>
              </View>
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      {(block.source_tags?.length || block.citations.length) ? (
        <SurfaceCard title="Source notes" subtitle="These labels show the traditions or reference frames behind this explanation.">
          <View style={styles.citationWrap}>
            {(block.source_tags?.length ? block.source_tags : block.citations).map((citation) => (
              <View key={citation} style={styles.citationChip}><Text style={styles.citationText}>{citation}</Text></View>
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      <SurfaceCard title="How to use this" subtitle="Move from the main interpretation into the supporting evidence as needed.">
        <Text style={styles.summary}>Start with the main interpretation. Then notice where it fits real life. If the wording feels abstract, come back to the chart evidence and the life translation instead of trying to memorize doctrine all at once.</Text>
      </SurfaceCard>

      <SecondaryButton label="Back to reading" onPress={onBack} icon={<Feather name="arrow-left" size={15} color={palette.ink} />} />
    </>
  );
}

const styles = StyleSheet.create({
  heroRow: { flexDirection: 'row', gap: 14, alignItems: 'center' },
  iconWrap: { width: 52, height: 52, borderRadius: 26, backgroundColor: palette.surface, borderWidth: 1, borderColor: palette.border, alignItems: 'center', justifyContent: 'center' },
  textWrap: { flex: 1, gap: 4 },
  title: { fontSize: 24, lineHeight: 31, color: palette.ink, fontWeight: '700' },
  subtitle: { fontSize: 13, lineHeight: 18, color: palette.muted },
  confidence: { fontSize: 13, lineHeight: 18, color: palette.muted, fontWeight: '700' },
  summary: { fontSize: 16, lineHeight: 26, color: palette.ink },
  supporting: { fontSize: 14, lineHeight: 22, color: palette.muted },
  evidenceStack: { gap: 14 },
  evidenceCard: { gap: 8, padding: 16, borderRadius: 16, borderWidth: 1, borderColor: palette.border, backgroundColor: palette.surface },
  evidenceLabel: { fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase', color: palette.ink, fontWeight: '700' },
  evidenceText: { fontSize: 14, lineHeight: 22, color: palette.ink },
  evidenceMeta: { fontSize: 12, lineHeight: 17, color: palette.muted, fontWeight: '600', textTransform: 'capitalize' },
  evidenceCaveat: { fontSize: 13, lineHeight: 20, color: palette.muted },
  citationWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  citationChip: { borderRadius: 999, backgroundColor: palette.white, borderWidth: 1, borderColor: palette.border, paddingHorizontal: 12, paddingVertical: 7 },
  citationText: { fontSize: 13, color: palette.muted, fontWeight: '600' },
  termCardWrap: { gap: 10 },
  termCard: { borderRadius: 14, borderWidth: 1, borderColor: palette.border, backgroundColor: palette.surface, padding: 14, gap: 6 },
  termTitle: { fontSize: 14, lineHeight: 19, color: palette.ink, fontWeight: '700' },
  termMeaning: { fontSize: 13, lineHeight: 19, color: palette.muted },
  caveatStack: { gap: 8 },
});
