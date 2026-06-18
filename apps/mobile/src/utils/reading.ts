import { GLOSSARY_BY_TERM } from '../content/glossary';
import { AnyReadingResponse, InterpretationBlock, ReadingHistoryDetailResponse, ReadingHistoryListResponse } from '../types/app';

const TEXT_REPLACEMENTS: Array<[RegExp, string]> = [
  [/worked through through/gi, 'worked through'],
  [/ability to act coherently/gi, 'how this topic acts and responds'],
  [/hidden enemies,\s*confinement,\s*and suffering/gi, 'hidden pressures, retreat, isolation, and the parts of life that stay behind the scenes'],
  [/Mixed testimony repeats here with medium confidence\.?/gi, 'The testimony here is mixed.'],
  [/constructive support rather than standing alone/gi, 'real support rather than being left to stand alone'],
  [/Tetrabiblos:\s*planetary quality/gi, 'Source note: classical planetary condition'],
];

function cleanString(value?: string | null) {
  if (!value) return value ?? null;
  let next = value;
  for (const [pattern, replacement] of TEXT_REPLACEMENTS) {
    next = next.replace(pattern, replacement);
  }
  next = next
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/([.?!]){2,}/g, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim();
  return next;
}

function cleanStringArray(values?: string[] | null) {
  if (!values?.length) return values ?? [];
  return values
    .map((value) => cleanString(value))
    .filter((value): value is string => Boolean(value));
}

function cleanSourceLabel(value: string) {
  const cleaned = cleanString(value) || value;
  if (/^Tetrabiblos:/i.test(cleaned)) {
    return cleaned.replace(/^Tetrabiblos:/i, 'Source note:');
  }
  return cleaned;
}

function sanitizeBlock(block: InterpretationBlock): InterpretationBlock {
  return {
    ...block,
    title: cleanString(block.title) || block.title,
    summary: cleanString(block.summary) || block.summary,
    citations: cleanStringArray(block.citations),
    caveats: cleanStringArray(block.caveats),
    plain_meaning: cleanString(block.plain_meaning),
    traditional_doctrine: cleanString(block.traditional_doctrine),
    chart_evidence: cleanStringArray(block.chart_evidence),
    life_translation: cleanString(block.life_translation),
    why_this_matters: cleanString(block.why_this_matters),
    confidence_explainer: cleanString(block.confidence_explainer),
    caveat: cleanString(block.caveat),
    source_tags: (block.source_tags ?? []).map(cleanSourceLabel),
    evidence_items: block.evidence_items.map((item) => ({
      ...item,
      observation: cleanString(item.observation) || item.observation,
      rule: cleanString(item.rule) || item.rule,
      interpretation: cleanString(item.interpretation) || item.interpretation,
      caveat: cleanString(item.caveat),
    })),
  };
}

export function sanitizeReadingResponse(result: AnyReadingResponse): AnyReadingResponse {
  return {
    ...result,
    reading: {
      ...result.reading,
      headline: cleanString(result.reading.headline) || result.reading.headline,
      practical_meaning: cleanString(result.reading.practical_meaning) || result.reading.practical_meaning,
      psychological_meaning: cleanString(result.reading.psychological_meaning) || result.reading.psychological_meaning,
      guidance: cleanString(result.reading.guidance) || result.reading.guidance,
      prompt: cleanString(result.reading.prompt),
      timing_focus: cleanString(result.reading.timing_focus),
      ritual_focus: cleanString(result.reading.ritual_focus),
      oracle: cleanString(result.reading.oracle),
    },
    notes: cleanStringArray(result.notes),
    source_lenses: result.source_lenses?.map((lens) => ({
      ...lens,
      labels: lens.labels.map(cleanSourceLabel),
    })),
    interpretation_blocks: result.interpretation_blocks.map(sanitizeBlock),
  };
}

export function sanitizeReadingHistoryListResponse(response: ReadingHistoryListResponse): ReadingHistoryListResponse {
  return {
    ...response,
    items: response.items.map((item) => ({
      ...item,
      headline: cleanString(item.headline) || item.headline,
      subject_label: cleanString(item.subject_label) || item.subject_label,
      reading_payload: sanitizeReadingResponse(item.reading_payload),
    })),
  };
}

export function sanitizeReadingHistoryDetailResponse(response: ReadingHistoryDetailResponse): ReadingHistoryDetailResponse {
  if (!response.item) return response;
  return {
    ...response,
    item: {
      ...response.item,
      headline: cleanString(response.item.headline) || response.item.headline,
      subject_label: cleanString(response.item.subject_label) || response.item.subject_label,
      reading_payload: sanitizeReadingResponse(response.item.reading_payload),
    },
  };
}

export function glossaryDefinition(term: string) {
  return GLOSSARY_BY_TERM[term.toLowerCase()] ?? null;
}
