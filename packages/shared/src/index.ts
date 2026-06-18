export type SourceLens = 'tetrabiblos' | 'jung' | 'red_book' | 'levi';

export interface CitationTag {
  id: string;
  lens: SourceLens;
  label: string;
}

export interface ForecastBlock {
  headline: string;
  practicalMeaning: string;
  psychologicalMeaning: string;
  guidance: string;
  prompt?: string;
  citations: CitationTag[];
}
