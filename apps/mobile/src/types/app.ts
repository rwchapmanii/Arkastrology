export type ReadingMode = 'natal' | 'synastry';
export type ScreenMode = 'auth' | 'onboarding' | 'reading' | 'detail' | 'account' | 'technical' | 'history';
export type PersonSlot = 'primary' | 'secondary';

export type ReadingSection = {
  headline: string;
  practical_meaning: string;
  life_translation?: string | null;
  psychological_meaning?: string | null;
  guidance: string;
  prompt?: string | null;
  timing_focus?: string | null;
  ritual_focus?: string | null;
  oracle?: string | null;
};

export type PredictionCard = {
  key: string;
  title: string;
  timeframe: string;
  summary: string;
  opportunities: string[];
  cautions: string[];
  rituals: string[];
  citations: string[];
};

export type EvidenceItem = {
  observation: string;
  rule: string;
  source_layer: string;
  interpretation: string;
  confidence_effect: string;
  caveat?: string | null;
};

export type InterpretationBlock = {
  block_type: string;
  title: string;
  summary: string;
  citations: string[];
  section_id?: string | null;
  topic_key?: string | null;
  confidence?: string | null;
  evidence_items: EvidenceItem[];
  caveats: string[];
  plain_meaning?: string | null;
  traditional_doctrine?: string | null;
  chart_evidence?: string[];
  life_translation?: string | null;
  why_this_matters?: string | null;
  confidence_explainer?: string | null;
  caveat?: string | null;
  technical_terms?: string[];
  source_tags?: string[];
  display_priority?: number;
  repeat_key?: string | null;
};

export type SourceLens = {
  lens: string;
  labels: string[];
};

export type BasicProfileResponse = {
  name?: string;
  latitude?: number | null;
  longitude?: number | null;
  utc_offset?: string | null;
  timezone_name?: string | null;
};

export type PlanetPlacement = {
  id: string;
  sign: string;
  sign_degree: number;
  longitude: number;
  house?: string | null;
  retrograde: boolean;
  longitude_speed?: number | null;
  movement_status?: string | null;
  house_condition?: string | null;
  sect_status?: string | null;
  visibility_status?: string | null;
  domicile_ruler?: string | null;
  essential_dignities: string[];
  essential_debilities: string[];
  triplicity_role?: string | null;
  term_ruler?: string | null;
  face_ruler?: string | null;
  in_house_joy: boolean;
  in_sign_joy: boolean;
  aversion_to_ascendant?: boolean | null;
  rules_houses: number[];
  traditional_strength?: string | null;
};

export type AnglePlacement = {
  id: string;
  sign: string;
  sign_degree: number;
  longitude: number;
};

export type HousePlacement = {
  id: string;
  sign: string;
  sign_degree: number;
  longitude: number;
};

export type AspectRecord = {
  first: string;
  second: string;
  type: string;
  degrees: number;
  orb: number;
};

export type SynastryAspectRecord = {
  first_owner: string;
  first: string;
  second_owner: string;
  second: string;
  type: string;
  degrees: number;
  orb: number;
};

export type TransitAspectRecord = {
  transit_body: string;
  transit_sign: string;
  transit_house?: string | null;
  natal_owner: string;
  natal_body: string;
  natal_sign: string;
  natal_house?: string | null;
  type: string;
  degrees: number;
  orb: number;
  phase?: string | null;
  exact_at?: string | null;
  peak_window_start?: string | null;
  peak_window_end?: string | null;
};

export type HouseRulerRecord = {
  house_number: number;
  sign: string;
  ruler: string;
  ruler_sign?: string | null;
  ruler_house?: string | null;
  ruler_strength?: string | null;
};

export type LotRecord = {
  name: string;
  formula: string;
  sign: string;
  sign_degree: number;
  longitude: number;
  house?: string | null;
  ruler: string;
  ruler_sign?: string | null;
  ruler_house?: string | null;
  ruler_strength?: string | null;
};

export type TraditionalContext = {
  zodiac: string;
  sect?: string | null;
  sect_light?: string | null;
  ascendant_sign?: string | null;
  ascendant_degree?: number | null;
  ascendant_ruler?: string | null;
  ascendant_ruler_sign?: string | null;
  ascendant_ruler_house?: string | null;
  ascendant_ruler_strength?: string | null;
  house_rulers: HouseRulerRecord[];
  fortune?: LotRecord | null;
  spirit?: LotRecord | null;
};

export type AnnualProfectionRecord = {
  age: number;
  activated_house: number;
  activated_sign: string;
  lord_of_year: string;
  lord_of_year_sign?: string | null;
  lord_of_year_house?: string | null;
  lord_of_year_strength?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
};

export type SolarReturnRecord = {
  solar_year: number;
  return_timestamp?: string | null;
  return_timezone?: string | null;
  location_status?: string | null;
  return_ascendant_sign?: string | null;
  return_ascendant_degree?: number | null;
  return_midheaven_sign?: string | null;
  return_midheaven_degree?: number | null;
  sun_house?: string | null;
  year_lord?: string | null;
  year_lord_house?: string | null;
  year_lord_strength?: string | null;
  angular_planets: string[];
};

export type TopicJudgmentRecord = {
  key: string;
  title: string;
  score: number;
  classification: string;
  confidence: string;
  relevant_houses: number[];
  relevant_lot?: string | null;
  evidence_items: EvidenceItem[];
  citations: string[];
};

export type YearMapRecord = {
  activated_house?: number | null;
  activated_house_title?: string | null;
  activated_topics: string[];
  profection_window?: string | null;
  lord_of_year?: string | null;
  lord_of_year_condition?: string | null;
  lord_of_year_house?: string | null;
  solar_return_ascendant?: string | null;
  solar_return_sun_house?: string | null;
  solar_return_year_lord_house?: string | null;
  solar_return_angular_planets: string[];
  fortune_emphasis?: string | null;
  spirit_emphasis?: string | null;
  fortune_spirit_alignment?: string | null;
  guidance?: string | null;
};

export type NatalTechnicalChart = {
  house_system: string;
  planets: PlanetPlacement[];
  angles: AnglePlacement[];
  houses: HousePlacement[];
  aspects: AspectRecord[];
  traditional_context?: TraditionalContext | null;
};

export type AnyReadingResponse = {
  chart_type: 'natal' | 'synastry';
  status: string;
  reading: ReadingSection;
  source_lenses?: SourceLens[];
  prediction_cards?: PredictionCard[];
  interpretation_blocks: InterpretationBlock[];
  notes: string[];
  technical_summary?: {
    house_system?: string;
    calculation_status?: string;
    input_resolution_status?: string;
    resolved_timezone?: string | null;
    primary_input_resolution_status?: string;
    secondary_input_resolution_status?: string;
    primary_resolved_timezone?: string | null;
    secondary_resolved_timezone?: string | null;
    precision_mode?: string | null;
    transit_timestamp?: string | null;
    transit_timezone?: string | null;
    transit_location_status?: string | null;
    chart_data?: NatalTechnicalChart;
    transit_chart_data?: NatalTechnicalChart;
    transit_aspects?: TransitAspectRecord[];
    annual_profection?: AnnualProfectionRecord | null;
    solar_return?: SolarReturnRecord | null;
    solar_return_chart_data?: NatalTechnicalChart | null;
    topic_judgments?: TopicJudgmentRecord[];
    year_map?: YearMapRecord | null;
    primary_chart_data?: NatalTechnicalChart;
    secondary_chart_data?: NatalTechnicalChart;
    inter_chart_aspects?: SynastryAspectRecord[];
    primary_transit_aspects?: TransitAspectRecord[];
    secondary_transit_aspects?: TransitAspectRecord[];
    primary_annual_profection?: AnnualProfectionRecord | null;
    secondary_annual_profection?: AnnualProfectionRecord | null;
    primary_solar_return?: SolarReturnRecord | null;
    secondary_solar_return?: SolarReturnRecord | null;
    primary_solar_return_chart_data?: NatalTechnicalChart | null;
    secondary_solar_return_chart_data?: NatalTechnicalChart | null;
  };
  profile?: BasicProfileResponse;
  primary_profile?: BasicProfileResponse;
  secondary_profile?: BasicProfileResponse;
};

export type PersonDraft = {
  profileLabel: string;
  name: string;
  birthDate: string;
  birthTime: string;
  birthCity: string;
  birthCountry: string;
  timePrecision: string;
  latitude: string;
  longitude: string;
  utcOffset: string;
  timezoneName: string;
  currentLatitude: string;
  currentLongitude: string;
  currentUtcOffset: string;
  currentTimezoneName: string;
};

export type AppDraft = {
  apiBaseUrl: string;
  readingMode: ReadingMode;
  includeJungian: boolean;
  includeRedBookPrompts: boolean;
  primary: PersonDraft;
  secondary: PersonDraft;
};

export type SavedPerson = {
  id: string;
  label: string;
  person: PersonDraft;
  savedAt: string;
};

export type PlaceResolveResponse = {
  status: string;
  resolved_place?: {
    normalized_name: string;
    latitude: number;
    longitude: number;
    timezone_name?: string | null;
    utc_offset?: string | null;
  } | null;
  place_candidates?: Array<{
    normalized_name: string;
    latitude: number;
    longitude: number;
    timezone_name?: string | null;
    utc_offset?: string | null;
  }>;
  notes: string[];
};

export type AccountPreferences = {
  include_jungian_default: boolean;
  include_red_book_prompts_default: boolean;
};

export type AccountProfile = {
  display_name?: string | null;
  timezone_name?: string | null;
  bio?: string | null;
  email_verified: boolean;
};

export type AuthState = {
  mode: 'signed_out' | 'guest' | 'authenticated';
  userId?: string;
  email?: string;
  token?: string;
  apiBaseUrl?: string;
  displayName?: string;
  plan?: string;
  sessionExpiresAt?: string;
  emailVerified?: boolean;
  timezoneName?: string;
  bio?: string;
  preferences: AccountPreferences;
};

export type AuthSessionResponse = {
  status: string;
  session_token: string;
  session_expires_at: string;
  account: {
    user_id: string;
    email: string;
    display_name?: string | null;
    plan: string;
    preferences: AccountPreferences;
    email_verified: boolean;
    timezone_name?: string | null;
    bio?: string | null;
  };
  notes: string[];
};

export type SessionStatusResponse = {
  status: string;
  session_expires_at: string;
  account: {
    user_id: string;
    email: string;
    display_name?: string | null;
    plan: string;
    preferences: AccountPreferences;
    email_verified: boolean;
    timezone_name?: string | null;
    bio?: string | null;
  };
};

export type TokenDeliveryResponse = {
  status: string;
  token_expires_at: string;
  delivery_mode: string;
  delivery_target: string;
  prototype_token?: string | null;
  notes: string[];
};

export type VerificationConfirmResponse = {
  status: string;
  email_verified: boolean;
  notes: string[];
};

export type PasswordResetConfirmResponse = {
  status: string;
  notes: string[];
};

export type AccountProfileResponse = {
  status: string;
  profile: AccountProfile;
};

export type ReadingHistoryTagFacet = {
  tag: string;
  count: number;
};

export type ReadingHistoryChartTypeFacet = {
  chart_type: string;
  count: number;
};

export type ReadingHistoryItem = {
  id: string;
  chart_type: 'natal' | 'synastry';
  status: string;
  headline: string;
  subject_label: string;
  created_at: string;
  updated_at?: string | null;
  favorite: boolean;
  tags: string[];
  reading_payload: AnyReadingResponse;
};

export type ReadingHistoryListResponse = {
  status: string;
  items: ReadingHistoryItem[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
  next_offset?: number | null;
  favorites_count: number;
  available_tags: ReadingHistoryTagFacet[];
  chart_type_counts: ReadingHistoryChartTypeFacet[];
};

export type ReadingHistoryDetailResponse = {
  status: string;
  item: ReadingHistoryItem;
};
