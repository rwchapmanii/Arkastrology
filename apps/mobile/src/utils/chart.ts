import { AspectRecord, PlanetPlacement, SynastryAspectRecord } from '../types/app';

export const SIGN_GLYPHS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];
export const TECHNICAL_ASPECT_TYPES = ['Conjunction', 'Sextile', 'Square', 'Trine', 'Opposition'] as const;

const SIGN_NAMES: Record<string, string> = {
  Aries: '♈', Taurus: '♉', Gemini: '♊', Cancer: '♋', Leo: '♌', Virgo: '♍',
  Libra: '♎', Scorpio: '♏', Sagittarius: '♐', Capricorn: '♑', Aquarius: '♒', Pisces: '♓',
};

const ASPECT_GLYPHS: Record<string, string> = {
  Conjunction: '☌',
  Sextile: '✶',
  Square: '□',
  Trine: '△',
  Opposition: '☍',
};

export function planetGlyph(id: string) {
  return {
    Sun: '☉', Moon: '☾', Mercury: '☿', Venus: '♀', Mars: '♂', Jupiter: '♃', Saturn: '♄', Asc: 'ASC', MC: 'MC', Desc: 'DSC', IC: 'IC',
  }[id] || id[0] || '•';
}

export function signGlyph(sign: string) {
  return SIGN_NAMES[sign] || sign;
}

export function formatDegree(value: number) {
  return `${value.toFixed(1)}°`;
}

function formatHouseLabel(house?: string | null) {
  if (!house) return 'House hidden in simple mode';
  return `House ${house.replace('House', '')}`;
}

export function formatPlanetSummary(planet: PlanetPlacement) {
  const traits = [
    planet.traditional_strength,
    planet.house_condition,
    planet.sect_status?.replace(/_/g, ' '),
    planet.visibility_status?.replace(/_/g, ' '),
    planet.retrograde ? 'retrograde' : null,
  ].filter(Boolean);
  return `${planetGlyph(planet.id)} ${planet.id} • ${signGlyph(planet.sign)} ${planet.sign} ${formatDegree(planet.sign_degree)} • ${formatHouseLabel(planet.house)}${traits.length ? ` • ${traits.join(' • ')}` : ''}`;
}

export function formatAspect(aspect: AspectRecord | SynastryAspectRecord) {
  if ('first_owner' in aspect) {
    const firstOwner = aspect.first_owner === 'primary' ? 'Person A' : 'Person B';
    const secondOwner = aspect.second_owner === 'primary' ? 'Person A' : 'Person B';
    return `${firstOwner} ${planetGlyph(aspect.first)} ${ASPECT_GLYPHS[aspect.type] || aspect.type} ${secondOwner} ${planetGlyph(aspect.second)} • distance from exact ${aspect.orb.toFixed(1)}°`;
  }
  return `${planetGlyph(aspect.first)} ${ASPECT_GLYPHS[aspect.type] || aspect.type} ${planetGlyph(aspect.second)} • distance from exact ${aspect.orb.toFixed(1)}°`;
}

export function aspectColor(type: string) {
  return {
    Conjunction: '#101010',
    Sextile: '#8B8B83',
    Trine: '#5D5D56',
    Square: '#32322D',
    Opposition: '#1A1A1A',
  }[type] || '#75756E';
}
