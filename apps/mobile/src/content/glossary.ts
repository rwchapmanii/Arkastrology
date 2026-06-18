export type GlossaryEntry = {
  term: string;
  meaning: string;
};

export const GLOSSARY_ENTRIES: GlossaryEntry[] = [
  { term: 'Annual profection', meaning: 'A traditional timing technique that moves the focus of life from one house to the next each birthday.' },
  { term: 'Lord of the year', meaning: 'The planet that rules the activated profection house and carries the main storyline of the year.' },
  { term: 'Sect', meaning: 'Whether the chart is a day chart or night chart. Sect changes how strongly and constructively certain planets tend to operate.' },
  { term: 'In sect', meaning: 'A planet is more comfortable because it belongs to the chart’s day or night team.' },
  { term: 'Contrary to sect', meaning: 'A planet is less comfortable because it is operating outside its preferred day or night condition.' },
  { term: 'Triplicity dignity', meaning: 'A form of traditional strength based on the element of the sign and whether the chart is day or night.' },
  { term: 'Succedent', meaning: 'A house with moderate strength: steadier than a cadent house, but less forceful than an angular house.' },
  { term: 'Angular', meaning: 'An angular house or planet acts more forcefully and tends to show itself more plainly in lived experience.' },
  { term: 'Cadent', meaning: 'A cadent house or planet tends to be less forceful, more indirect, and slower to show itself outwardly.' },
  { term: 'Fortune', meaning: 'A calculated point connected with the body, circumstances, material conditions, and what happens to the native.' },
  { term: 'Spirit', meaning: 'A calculated point connected with intention, choice, action, and what the native deliberately pursues.' },
  { term: 'Mixed testimony', meaning: 'The chart gives both supportive and difficult indications about the same topic.' },
  { term: 'Bonification', meaning: 'A planet or topic receives help from a benefic such as Jupiter or Venus.' },
  { term: 'Maltreatment', meaning: 'A planet or topic receives difficult pressure from a malefic such as Mars or Saturn.' },
];

export const GLOSSARY_BY_TERM = Object.fromEntries(
  GLOSSARY_ENTRIES.map((entry) => [entry.term.toLowerCase(), entry.meaning]),
) as Record<string, string>;
