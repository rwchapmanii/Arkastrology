from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class BirthProfile(BaseModel):
    name: str = Field(..., description="Display name for the chart owner")
    birth_date: str = Field(..., description="YYYY-MM-DD")
    birth_time: str = Field(..., description="HH:MM or HH:MM:SS")
    birth_city: str
    birth_country: str
    time_precision: str = Field(..., description="exact | approximate | unknown")
    latitude: Optional[float] = Field(default=None, description="Decimal latitude for chart calculation")
    longitude: Optional[float] = Field(default=None, description="Decimal longitude for chart calculation")
    utc_offset: Optional[str] = Field(default=None, description="UTC offset like -05:00 or +01:00")
    timezone_name: Optional[str] = Field(default=None, description="IANA timezone name, e.g. America/Detroit")
    current_latitude: Optional[float] = Field(default=None, description="Current decimal latitude for live transit houses")
    current_longitude: Optional[float] = Field(default=None, description="Current decimal longitude for live transit houses")
    current_utc_offset: Optional[str] = Field(default=None, description="Current UTC offset like -04:00 for live transit timing")
    current_timezone_name: Optional[str] = Field(default=None, description="Current IANA timezone name for live transit timing")


class NatalReadingRequest(BaseModel):
    profile: BirthProfile
    include_technical: bool = True
    include_jungian: bool = False
    include_red_book_prompts: bool = False


class SynastryReadingRequest(BaseModel):
    primary_profile: BirthProfile
    secondary_profile: BirthProfile
    include_technical: bool = True
    include_jungian: bool = False
    include_red_book_prompts: bool = False


class PlaceResolveRequest(BaseModel):
    city: str
    country: str
    birth_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    birth_time: Optional[str] = Field(default=None, description="HH:MM or HH:MM:SS")
    limit: int = Field(default=3, ge=1, le=5)


class ResolvedPlace(BaseModel):
    query: str
    normalized_name: str
    latitude: float
    longitude: float
    timezone_name: Optional[str] = None
    utc_offset: Optional[str] = None


class PlaceResolveResponse(BaseModel):
    status: str
    resolved_place: Optional[ResolvedPlace] = None
    place_candidates: List[ResolvedPlace] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class PlanetPlacement(BaseModel):
    id: str
    sign: str
    sign_degree: float
    longitude: float
    house: Optional[str] = None
    retrograde: bool
    longitude_speed: Optional[float] = None
    movement_status: Optional[str] = None
    house_condition: Optional[str] = None
    sect_status: Optional[str] = None
    visibility_status: Optional[str] = None
    domicile_ruler: Optional[str] = None
    essential_dignities: List[str] = Field(default_factory=list)
    essential_debilities: List[str] = Field(default_factory=list)
    triplicity_role: Optional[str] = None
    term_ruler: Optional[str] = None
    face_ruler: Optional[str] = None
    in_house_joy: bool = False
    in_sign_joy: bool = False
    aversion_to_ascendant: Optional[bool] = None
    rules_houses: List[int] = Field(default_factory=list)
    traditional_strength: Optional[str] = None


class AnglePlacement(BaseModel):
    id: str
    sign: str
    sign_degree: float
    longitude: float


class HousePlacement(BaseModel):
    id: str
    sign: str
    sign_degree: float
    longitude: float


class AspectRecord(BaseModel):
    first: str
    second: str
    type: str
    degrees: int
    orb: float


class SynastryAspectRecord(BaseModel):
    first_owner: str
    first: str
    second_owner: str
    second: str
    type: str
    degrees: int
    orb: float


class TransitAspectRecord(BaseModel):
    transit_body: str
    transit_sign: str
    transit_house: Optional[str] = None
    natal_owner: str = "self"
    natal_body: str
    natal_sign: str
    natal_house: Optional[str] = None
    type: str
    degrees: int
    orb: float
    phase: Optional[str] = None
    exact_at: Optional[str] = None
    peak_window_start: Optional[str] = None
    peak_window_end: Optional[str] = None


class HouseRulerRecord(BaseModel):
    house_number: int
    sign: str
    ruler: str
    ruler_sign: Optional[str] = None
    ruler_house: Optional[str] = None
    ruler_strength: Optional[str] = None


class LotRecord(BaseModel):
    name: str
    formula: str
    sign: str
    sign_degree: float
    longitude: float
    house: Optional[str] = None
    ruler: str
    ruler_sign: Optional[str] = None
    ruler_house: Optional[str] = None
    ruler_strength: Optional[str] = None


class TraditionalContext(BaseModel):
    zodiac: str = "tropical"
    sect: Optional[str] = None
    sect_light: Optional[str] = None
    ascendant_sign: Optional[str] = None
    ascendant_degree: Optional[float] = None
    ascendant_ruler: Optional[str] = None
    ascendant_ruler_sign: Optional[str] = None
    ascendant_ruler_house: Optional[str] = None
    ascendant_ruler_strength: Optional[str] = None
    house_rulers: List[HouseRulerRecord] = Field(default_factory=list)
    fortune: Optional[LotRecord] = None
    spirit: Optional[LotRecord] = None


class AnnualProfectionRecord(BaseModel):
    age: int
    activated_house: int
    activated_sign: str
    lord_of_year: str
    lord_of_year_sign: Optional[str] = None
    lord_of_year_house: Optional[str] = None
    lord_of_year_strength: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None


class SolarReturnRecord(BaseModel):
    solar_year: int
    return_timestamp: Optional[str] = None
    return_timezone: Optional[str] = None
    location_status: Optional[str] = None
    return_ascendant_sign: Optional[str] = None
    return_ascendant_degree: Optional[float] = None
    return_midheaven_sign: Optional[str] = None
    return_midheaven_degree: Optional[float] = None
    sun_house: Optional[str] = None
    year_lord: Optional[str] = None
    year_lord_house: Optional[str] = None
    year_lord_strength: Optional[str] = None
    angular_planets: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    observation: str
    rule: str
    source_layer: str = "traditional_core"
    interpretation: str
    confidence_effect: str
    caveat: Optional[str] = None
    polarity: Optional[str] = None
    weight: Optional[int] = None
    chart_context: Optional[str] = None


class TopicJudgmentRecord(BaseModel):
    key: str
    title: str
    score: int
    classification: str
    confidence: str
    activation_score: int = 0
    support_score: int = 0
    strain_score: int = 0
    relevant_houses: List[int] = Field(default_factory=list)
    relevant_lot: Optional[str] = None
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    challenging_evidence: List[EvidenceItem] = Field(default_factory=list)
    activating_evidence: List[EvidenceItem] = Field(default_factory=list)
    synthesis: Optional[str] = None
    validation_notes: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


class YearMapRecord(BaseModel):
    activated_house: Optional[int] = None
    activated_house_title: Optional[str] = None
    activated_topics: List[str] = Field(default_factory=list)
    profection_window: Optional[str] = None
    lord_of_year: Optional[str] = None
    lord_of_year_condition: Optional[str] = None
    lord_of_year_house: Optional[str] = None
    solar_return_ascendant: Optional[str] = None
    solar_return_sun_house: Optional[str] = None
    solar_return_year_lord_house: Optional[str] = None
    solar_return_angular_planets: List[str] = Field(default_factory=list)
    fortune_emphasis: Optional[str] = None
    spirit_emphasis: Optional[str] = None
    fortune_spirit_alignment: Optional[str] = None
    fortune_spirit_axis: Optional[str] = None
    annual_patterns: List[str] = Field(default_factory=list)
    guidance: Optional[str] = None


class NatalTechnicalChart(BaseModel):
    house_system: str
    planets: List[PlanetPlacement]
    angles: List[AnglePlacement]
    houses: List[HousePlacement]
    aspects: List[AspectRecord]
    traditional_context: Optional[TraditionalContext] = None


class TechnicalSummary(BaseModel):
    calculation_status: str
    engine_status: str
    available_ontology_counts: Dict[str, int]
    house_system: str
    supported_planets: List[str]
    supported_aspects: List[str]
    input_resolution_status: str = "manual"
    resolved_timezone: Optional[str] = None
    precision_mode: Optional[str] = None
    chart_data: Optional[NatalTechnicalChart] = None
    transit_timestamp: Optional[str] = None
    transit_timezone: Optional[str] = None
    transit_location_status: Optional[str] = None
    transit_chart_data: Optional[NatalTechnicalChart] = None
    transit_aspects: List[TransitAspectRecord] = Field(default_factory=list)
    annual_profection: Optional[AnnualProfectionRecord] = None
    solar_return: Optional[SolarReturnRecord] = None
    solar_return_chart_data: Optional[NatalTechnicalChart] = None
    topic_judgments: List[TopicJudgmentRecord] = Field(default_factory=list)
    year_map: Optional[YearMapRecord] = None


class SynastryTechnicalSummary(BaseModel):
    calculation_status: str
    engine_status: str
    available_ontology_counts: Dict[str, int]
    house_system: str
    supported_planets: List[str]
    supported_aspects: List[str]
    primary_input_resolution_status: str = "manual"
    secondary_input_resolution_status: str = "manual"
    primary_resolved_timezone: Optional[str] = None
    secondary_resolved_timezone: Optional[str] = None
    precision_mode: Optional[str] = None
    primary_chart_data: Optional[NatalTechnicalChart] = None
    secondary_chart_data: Optional[NatalTechnicalChart] = None
    inter_chart_aspects: List[SynastryAspectRecord] = Field(default_factory=list)
    transit_timestamp: Optional[str] = None
    transit_timezone: Optional[str] = None
    transit_location_status: Optional[str] = None
    transit_chart_data: Optional[NatalTechnicalChart] = None
    primary_transit_aspects: List[TransitAspectRecord] = Field(default_factory=list)
    secondary_transit_aspects: List[TransitAspectRecord] = Field(default_factory=list)
    primary_annual_profection: Optional[AnnualProfectionRecord] = None
    secondary_annual_profection: Optional[AnnualProfectionRecord] = None
    primary_solar_return: Optional[SolarReturnRecord] = None
    secondary_solar_return: Optional[SolarReturnRecord] = None
    primary_solar_return_chart_data: Optional[NatalTechnicalChart] = None
    secondary_solar_return_chart_data: Optional[NatalTechnicalChart] = None
    topic_judgments: List[TopicJudgmentRecord] = Field(default_factory=list)


class ReadingSection(BaseModel):
    headline: str
    practical_meaning: str
    life_translation: Optional[str] = None
    psychological_meaning: Optional[str] = None
    guidance: str
    prompt: Optional[str] = None
    timing_focus: Optional[str] = None
    ritual_focus: Optional[str] = None
    oracle: Optional[str] = None


class PredictionCard(BaseModel):
    key: str
    title: str
    timeframe: str
    summary: str
    opportunities: List[str] = Field(default_factory=list)
    cautions: List[str] = Field(default_factory=list)
    rituals: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


class DailyHoroscope(BaseModel):
    title: str
    date: str
    headline: str
    overview: Optional[str] = None
    focus: Optional[str] = None
    opportunity: Optional[str] = None
    caution: Optional[str] = None
    action: Optional[str] = None
    main_transit: Optional[str] = None
    day_thesis: Optional[str] = None
    what_this_means: List[str] = Field(default_factory=list)
    why_the_chart_says_this: List[str] = Field(default_factory=list)
    larger_story: Optional[str] = None
    opportunities: List[str] = Field(default_factory=list)
    watch_fors: List[str] = Field(default_factory=list)
    best_move_primary: Optional[str] = None
    best_move_supporting: List[str] = Field(default_factory=list)
    timing: str
    active_transits: List[str] = Field(default_factory=list)
    action_checklist: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


class SourceLens(BaseModel):
    lens: str
    labels: List[str]


class InterpretationBlock(BaseModel):
    block_type: str
    title: str
    summary: str
    citations: List[str]
    section_id: Optional[str] = None
    topic_key: Optional[str] = None
    confidence: Optional[str] = None
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    plain_meaning: Optional[str] = None
    traditional_doctrine: Optional[str] = None
    chart_evidence: List[str] = Field(default_factory=list)
    life_translation: Optional[str] = None
    why_this_matters: Optional[str] = None
    confidence_explainer: Optional[str] = None
    caveat: Optional[str] = None
    technical_terms: List[str] = Field(default_factory=list)
    source_tags: List[str] = Field(default_factory=list)
    display_priority: int = 100
    repeat_key: Optional[str] = None


class NatalReadingResponse(BaseModel):
    chart_type: str = "natal"
    status: str
    profile: BirthProfile
    technical_summary: TechnicalSummary
    reading: ReadingSection
    daily_horoscope: Optional[DailyHoroscope] = None
    source_lenses: List[SourceLens]
    prediction_cards: List[PredictionCard] = Field(default_factory=list)
    interpretation_blocks: List[InterpretationBlock] = Field(default_factory=list)
    notes: List[str]


class SynastryReadingResponse(BaseModel):
    chart_type: str = "synastry"
    status: str
    primary_profile: BirthProfile
    secondary_profile: BirthProfile
    technical_summary: SynastryTechnicalSummary
    reading: ReadingSection
    daily_horoscope: Optional[DailyHoroscope] = None
    source_lenses: List[SourceLens]
    prediction_cards: List[PredictionCard] = Field(default_factory=list)
    interpretation_blocks: List[InterpretationBlock] = Field(default_factory=list)
    notes: List[str]
