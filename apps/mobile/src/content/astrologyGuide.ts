export type GuideSection = {
  title: string;
  paragraphs?: string[];
  bullets?: string[];
};

export const astrologyGuideSections: GuideSection[] = [
  {
    title: 'What astrology means in The Ark',
    paragraphs: [
      'The Ark treats astrology as a traditional rule-based interpretive discipline, not as a scientifically proven diagnostic science. It starts with astronomical positions — date, time, place, and angular relationships — and then interprets those patterns through a traditional chart-reading method.',
      'In practical terms, the app is asking: What was the sky map at birth? Which parts of the chart repeat the same testimony? What life topics do those chart factors govern? And what is active in the sky now as a supplemental timing layer?'
    ]
  },
  {
    title: 'Where this app gets its language',
    paragraphs: [
      'The Ark now treats the traditional astrology research report as its doctrinal source of truth. The intended core is ancient and traditional chart judgment: whole-sign houses, the seven visible planets, chart structure, house topics, and repeated testimony.',
      'Modern psychological or imaginal material can still be useful, but it belongs in an optional overlay. It should never silently replace the historical core or pretend to be the same thing.'
    ],
    bullets: [
      'Traditional core: whole-sign houses, seven visible planets, house topics, major aspects, and chart structure',
      'Traditional expansion path: sect, house rulers, planetary condition, Lots of Fortune and Spirit, and repeated testimony',
      'Optional modern overlay: Jungian interpretation and other psychology-oriented language',
      'Optional reflective overlay: journaling and imaginal prompts that do not override the chart structure'
    ]
  },
  {
    title: 'Astronomy and astrology: the difference',
    paragraphs: [
      'Astronomy measures the sky. Astrology interprets the meaning of the measured sky. The Ark uses astronomical chart positions under the hood, then builds astrological interpretation on top of those positions.',
      'So the app is not guessing randomly. It calculates a chart from birth data, then reads that chart through its internal astrology framework.'
    ]
  },
  {
    title: 'How The Ark builds a chart',
    paragraphs: [
      'The app calculates a chart from birth date, birth time, UTC offset, latitude, and longitude. If place information is incomplete, it can try to resolve it from city, country, and date context. If birth time is not exact, the app switches into a simpler mode instead of pretending the full chart is equally certain.',
      'The Ark currently uses Whole Sign houses as its house system. It calculates the seven visible planets it focuses on most directly: Sun, Moon, Mercury, Venus, Mars, Jupiter, and Saturn. It also uses the Ascendant and Midheaven when birth-time accuracy allows them.'
    ],
    bullets: [
      'Exact birth time = fuller chart with houses, angles, and more precise timing',
      'Approximate or unknown birth time = simple mode with planets and stable patterns only',
      'Birth place matters because location changes houses and angles',
      'Current location can also matter for live transit timing'
    ]
  },
  {
    title: 'How a traditional reading is judged',
    paragraphs: [
      'A traditional reading does not treat one placement as the whole story. It starts with chart structure: whether the chart is by day or by night, which sign rises, which planet rules that sign, and which houses and planets repeat the same testimony.',
      'The Ark already uses the traditional astronomical skeleton. The next layer being surfaced more directly in the product is the deeper judgment stack: sect, house rulership, planetary condition, Lots of Fortune and Spirit, and repeated testimony across multiple factors.'
    ],
    bullets: [
      'Judge chart structure before jumping to personality language',
      'Read a life topic through the house, its ruler, and any planets placed there',
      'Repeated testimony raises confidence; contradictions lower it',
      'Modern psychological or imaginal layers are optional overlays, not the historical source core'
    ]
  },
  {
    title: 'The planets: what each one means here',
    bullets: [
      'Sun: identity, purpose, leadership, recognition. The app treats this as the core self and life direction.',
      'Moon: body, mood, memory, habit. The app treats this as emotional style, reactivity, and felt safety.',
      'Mercury: language, analysis, communication, learning. This shows how the mind links things and explains them.',
      'Venus: affection, value, intimacy, taste. This describes attraction, value, reciprocity, and what feels beautiful or worthwhile.',
      'Mars: assertion, anger, courage, desire. This shows drive, friction, boundary-setting, and direct action.',
      'Jupiter: belief, opportunity, teaching, expansion. This points toward growth, meaning, faith, and larger horizons.',
      'Saturn: duty, discipline, limits, endurance. This shows structure, pressure, maturity, responsibility, and time.'
    ]
  },
  {
    title: 'The signs: how energy expresses itself',
    paragraphs: [
      'In The Ark, signs describe style. A planet tells you what part of life is speaking; the sign tells you how it speaks.'
    ],
    bullets: [
      'Aries: direct, forceful, initiating',
      'Taurus: stable, embodied, enduring',
      'Gemini: curious, mobile, linguistic',
      'Cancer: protective, receptive, containing',
      'Leo: radiant, expressive, sovereign',
      'Virgo: precise, analytic, refining',
      'Libra: balancing, relational, harmonizing',
      'Scorpio: intense, penetrating, secretive',
      'Sagittarius: expansive, seeking, philosophical',
      'Capricorn: disciplined, pragmatic, enduring',
      'Aquarius: conceptual, systemic, distanced',
      'Pisces: imaginal, permeable, yielding'
    ]
  },
  {
    title: 'The houses: where life events show up',
    paragraphs: [
      'In The Ark, houses answer the question: what part of life is this most likely to show up in?'
    ],
    bullets: [
      '1st House: body, presence, character, self-presentation',
      '2nd House: money, possessions, livelihood, support',
      '3rd House: siblings, messages, local travel, study',
      '4th House: home, parents, land, roots',
      '5th House: joy, romance, creativity, performance',
      '6th House: labor, illness, service, repair',
      '7th House: marriage, contracts, committed partnerships, open opponents',
      '8th House: inheritance, fear, debt, other people’s resources',
      '9th House: belief, long travel, higher study, worldview',
      '10th House: career, status, calling',
      '11th House: community, networks, future aims',
      '12th House: hidden pressures, retreat, isolation, and what stays behind the scenes'
    ]
  },
  {
    title: 'Aspects: how parts of the chart relate to each other',
    paragraphs: [
      'Aspects are angular relationships between planets. The Ark uses five major aspect types and explains them as relationship patterns inside the chart or between two charts.'
    ],
    bullets: [
      'Conjunction: planets join and intensify each other. The app treats this as concentration or activation.',
      'Sextile: supportive opening. The app treats this as a practical opportunity or usable bridge.',
      'Square: friction and trial. The app treats this as a growth demand that needs effort and maturity.',
      'Trine: natural flow. The app treats this as ease that still needs stewardship.',
      'Opposition: polarity and mirror. The app treats this as a revealing encounter with the other side of the pattern.'
    ]
  },
  {
    title: 'Planetary movement and current sky timing',
    paragraphs: [
      'A birth chart is the fixed starting map. Transits are the moving sky now. The Ark currently compares the moving sky to the birth chart to explain why certain themes feel louder at a given time, but that current-sky layer is supplemental rather than the full traditional timing stack.',
      'Some bodies move faster than others in lived experience. The Moon changes the fastest and often shows up as mood, atmosphere, body memory, and emotional tone. Saturn is slower and often shows up as duty, pressure, structure, or long-term tests. The longer-term traditional plan is to pair that live sky weather with profections and other time-lord methods.'
    ],
    bullets: [
      'Transit = current sky contacting the birth chart',
      'Distance from exact = how close a transit or aspect is to its strongest point',
      'Retrograde = a body appearing to move backward from the Earth-based viewpoint used by the chart'
    ]
  },
  {
    title: 'Relationship readings',
    paragraphs: [
      'A relationship reading compares two charts. The Ark is not trying to give a shallow compatibility score. It is looking for repeated patterns of attraction, support, friction, alliance, conduct, and emotional bond between two people.',
      'That is why the app increasingly uses the phrase relationship reading instead of only using the technical word synastry. The goal is to teach what the pattern does, not only what astrologers call it.'
    ]
  },
  {
    title: 'Abbreviations and chart terms',
    bullets: [
      'Asc = Ascendant = rising sign = how you first come across and enter situations',
      'MC = Midheaven = the career, public, or calling angle',
      'UTC offset = the time difference used to place the chart correctly in time',
      'Retrograde = apparent backward motion from the Earth-based viewpoint',
      'Distance from exact = how close an aspect is to its strongest expression',
      'Whole Sign = the house system The Ark uses by default',
      'Simple mode = the app intentionally limits claims when birth time is not exact'
    ]
  },
  {
    title: 'What makes The Ark different',
    paragraphs: [
      'The Ark is different because it is trying to become both more traditional and more honest at the same time. It begins with chart structure, then labels any modern overlay instead of blurring everything into one voice.',
      'It is also designed to be honest about certainty. If the birth time is incomplete, the app does not pretend to know exact houses and angles. It moves into simple mode and tells the user what is still readable and what is not yet reliable.'
    ],
    bullets: [
      'Whole-sign technical charting',
      'A source-grounded traditional core with optional modern overlays',
      'Context-specific aspect policy for natal, relationship, and transit readings',
      'Place and timezone resolution from birth context when needed',
      'A layered reading method that keeps the historical core distinct from reflective additions',
      'A teaching-oriented interface rather than a raw technical dump'
    ]
  },
  {
    title: 'How to use the app well',
    bullets: [
      'Start with the main reading before diving into the deepest technical material.',
      'Use the chart map as a visual orientation tool, not as a test you must decode perfectly.',
      'Open the guide when you need definitions, context, or a slower explanation.',
      'Treat one or two repeated themes as more important than trying to memorize every sentence.',
      'If the birth time is uncertain, trust the simpler parts of the reading more than the timed details.',
      'Use the detail screens to connect chart language to real-life behavior, choices, and relationships.'
    ]
  },
  {
    title: 'What this guide is built from',
    paragraphs: [
      'This guide is based on The Ark project itself: the repo README, the API README, the chart engine, aspect policy, profile resolution logic, house-system settings, and the internal ontology files for planets, signs, houses, aspects, transit thresholds, and the optional overlay files such as Jungian mappings and Lévi currents.',
      'In other words, this guide is describing the actual app you are using, not a generic outside astrology summary pasted in from somewhere else.'
    ]
  }
];
