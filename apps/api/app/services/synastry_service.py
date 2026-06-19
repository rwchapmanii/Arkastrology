from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.models.chart import (
    AnnualProfectionRecord,
    BirthProfile,
    EvidenceItem,
    InterpretationBlock,
    NatalTechnicalChart,
    PredictionCard,
    ReadingSection,
    SolarReturnRecord,
    SourceLens,
    SynastryAspectRecord,
    SynastryReadingRequest,
    SynastryReadingResponse,
    SynastryTechnicalSummary,
    TopicJudgmentRecord,
)
from app.services.aspect_service import AspectPolicyService
from app.services.astrology_settings import DEFAULT_HOUSE_SYSTEM_LABEL
from app.services.chart_engine import ChartEngineError, NatalChartEngine
from app.services.citation_service import CitationService
from app.services.content_loader import load_ontology
from app.services.interpretation_service import NatalInterpretationService
from app.services.profile_resolution_service import ProfileResolutionService
from app.services.reading_llm_service import ReadingLLMService
from app.services.traditional_astrology_service import TraditionalAstrologyService
from app.services.transit_service import TransitForecastService


class SynastryReadingService:
    INTEREST_PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
    BENEFICS = {"Venus", "Jupiter"}
    MALEFICS = {"Mars", "Saturn"}
    SIGN_ORDER = [
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    ]
    SIGN_INDEX = {sign: index for index, sign in enumerate(SIGN_ORDER)}
    TOPIC_CONFIGS = [
        {
            "key": "partnership_agreements",
            "title": "Partnership and agreements",
            "house_numbers": [7],
            "lot": None,
            "relationship_lots": ["Fortune", "Spirit"],
            "helper_planets": ["Venus", "Sun", "Moon"],
            "bridge_pairs": [("Sun", "Moon"), ("Moon", "Sun"), ("Venus", "Venus"), ("Venus", "Moon"), ("Moon", "Venus")],
            "hard_aspect_penalty": 2,
            "priority_bias": 3,
        },
        {
            "key": "attraction_intimacy",
            "title": "Attraction, intimacy, and pursuit",
            "house_numbers": [5, 7, 8],
            "lot": "Fortune",
            "relationship_lots": ["Fortune"],
            "helper_planets": ["Venus", "Mars", "Moon"],
            "bridge_pairs": [("Venus", "Mars"), ("Mars", "Venus"), ("Moon", "Venus"), ("Venus", "Moon")],
            "hard_aspect_penalty": 1,
            "priority_bias": 2,
        },
        {
            "key": "communication_alliance",
            "title": "Communication and alliance",
            "house_numbers": [3, 11],
            "lot": None,
            "relationship_lots": ["Spirit"],
            "helper_planets": ["Mercury", "Moon", "Jupiter"],
            "bridge_pairs": [("Mercury", "Mercury"), ("Mercury", "Moon"), ("Moon", "Mercury"), ("Mercury", "Jupiter"), ("Jupiter", "Mercury")],
            "hard_aspect_penalty": 2,
            "priority_bias": 1,
        },
        {
            "key": "home_foundation",
            "title": "Home, care, and foundations",
            "house_numbers": [4],
            "lot": "Fortune",
            "relationship_lots": ["Fortune"],
            "helper_planets": ["Moon", "Venus", "Saturn"],
            "bridge_pairs": [("Moon", "Moon"), ("Moon", "Venus"), ("Venus", "Moon"), ("Moon", "Saturn"), ("Saturn", "Moon")],
            "hard_aspect_penalty": 2,
            "priority_bias": 1,
        },
        {
            "key": "shared_work_direction",
            "title": "Shared work, purpose, and direction",
            "house_numbers": [10, 11],
            "lot": "Spirit",
            "relationship_lots": ["Spirit"],
            "helper_planets": ["Sun", "Jupiter", "Saturn"],
            "bridge_pairs": [("Sun", "Sun"), ("Sun", "Jupiter"), ("Jupiter", "Sun"), ("Jupiter", "Saturn"), ("Saturn", "Jupiter")],
            "hard_aspect_penalty": 2,
            "priority_bias": 2,
        },
    ]

    @staticmethod
    def _simple_closeness(aspect: SynastryAspectRecord) -> str:
        if aspect.orb <= 2:
            return "very close"
        if aspect.orb <= 4:
            return "fairly close"
        return "present but looser"

    @staticmethod
    def _build_source_lenses(request: SynastryReadingRequest) -> List[SourceLens]:
        source_lenses = [
            SourceLens(
                lens="traditional_core",
                labels=[
                    "Ancient and traditional core: each natal chart includes sect, house rulers, planetary condition, and Fortune/Spirit",
                    "Traditional timing core: annual profections and solar returns are exposed per person before relationship synthesis",
                    "Traditional method: relationship judgment should rest on natal structure before cross-chart interpretation",
                ],
            ),
            SourceLens(
                lens="relationship_synthesis",
                labels=[
                    "Relationship synthesis: prose begins with each person's natal condition, activated house, year lord, and solar return emphasis",
                    "Relationship synthesis: cross-chart aspects are judged after the natal frames and yearly activations are established",
                    "Relationship synthesis: relationship topics are judged by each person's natal topic condition, then by ruler contacts, helper planets, and yearly activation",
                ],
            ),
            SourceLens(
                lens="app_synthesis",
                labels=[
                    "App synthesis: explanatory relationship language is supplemental and must not override structural testimony",
                ],
            ),
            SourceLens(
                lens="current_sky",
                labels=[
                    "Supplemental current-sky layer: live transit chart anchored to the current shared field",
                    "Supplemental current-sky layer: near-term weather is not the full traditional timing stack",
                ],
            ),
        ]
        if request.include_jungian:
            source_lenses.append(
                SourceLens(
                    lens="modern_psychology",
                    labels=[
                        "Modern optional overlay: Jungian projection and mirror language",
                        "Modern optional overlay: psychology does not override chart structure",
                    ],
                )
            )
        if request.include_red_book_prompts:
            source_lenses.append(
                SourceLens(
                    lens="modern_reflection",
                    labels=["Modern optional layer: imaginal and journaling prompts"],
                )
            )
        return source_lenses

    @staticmethod
    def _planet_lookup(chart_data: NatalTechnicalChart, planet_name: str):
        return next((planet for planet in chart_data.planets if planet.id == planet_name), None)

    @staticmethod
    def _house_lookup(ontology: Dict) -> Dict[int, Dict]:
        return {item["house_number"]: item for item in ontology["houses"]}

    @staticmethod
    def _topic_phrase(values: List[str], limit: int = 2) -> str:
        items = values[:limit]
        if not items:
            return "life themes"
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return ", ".join(items[:-1]) + f", and {items[-1]}"

    @classmethod
    def _house_title_for_id(cls, ontology: Dict, house_id: Optional[str]) -> str:
        if not house_id:
            return "an unknown place"
        house_number = cls._house_number(house_id)
        return cls._house_lookup(ontology).get(house_number, {}).get("display_name", house_id)

    @classmethod
    def _house_topics_for_number(cls, ontology: Dict, house_number: Optional[int]) -> str:
        if not house_number:
            return "life themes"
        house_meta = cls._house_lookup(ontology).get(house_number, {})
        return cls._topic_phrase(house_meta.get("classical_topics", []) or house_meta.get("modern_topics", []), 3)

    @classmethod
    def _sign_distance(cls, start_sign: str, end_sign: str) -> int:
        return (cls.SIGN_INDEX[end_sign] - cls.SIGN_INDEX[start_sign]) % 12

    @classmethod
    def _sign_relation(cls, start_sign: str, end_sign: str) -> Optional[str]:
        distance = cls._sign_distance(start_sign, end_sign)
        return {
            0: "Conjunction",
            2: "Sextile",
            3: "Square",
            4: "Trine",
            6: "Opposition",
            8: "Trine",
            9: "Square",
            10: "Sextile",
        }.get(distance)

    @classmethod
    def _is_superior_witness(cls, witness_sign: str, target_sign: str) -> bool:
        return cls._sign_distance(witness_sign, target_sign) in {2, 3, 4}

    @staticmethod
    def _topic_score_bucket(score: int) -> str:
        if score >= 4:
            return "supportive"
        if score <= -4:
            return "difficult"
        return "mixed"

    @staticmethod
    def _confidence_label(evidence_count: int, score: int) -> str:
        if evidence_count >= 5 and abs(score) >= 5:
            return "high"
        if evidence_count >= 3:
            return "medium"
        return "low"

    @staticmethod
    def _confidence_effect_from_score(score: int) -> str:
        if score > 0:
            return "supports"
        if score < 0:
            return "pressures"
        return "qualifies"

    @classmethod
    def _evidence_item(
        cls,
        observation: str,
        rule: str,
        interpretation: str,
        score: int,
        caveat: Optional[str] = None,
        source_layer: str = "relationship_synthesis",
    ) -> EvidenceItem:
        combined = f"{observation} {rule}".lower()
        resolved_source_layer = source_layer
        if source_layer == "relationship_synthesis":
            if any(token in combined for token in ["annual profection", "solar return", "year lord", "profection year"]):
                resolved_source_layer = "traditional_timing"
            elif any(token in combined for token in ["fortune", "spirit", "sect", "house ruler", "domicile ruler"]):
                resolved_source_layer = "traditional_core"
            elif any(token in combined for token in ["transit", "current sky", "moving sky"]):
                resolved_source_layer = "current_sky"
        return EvidenceItem(
            observation=observation,
            rule=rule,
            source_layer=resolved_source_layer,
            interpretation=interpretation,
            confidence_effect=cls._confidence_effect_from_score(score),
            caveat=caveat,
        )

    @classmethod
    def _topic_record_score(cls, record: TopicJudgmentRecord) -> int:
        if record.score >= 6:
            return 3
        if record.score >= 2:
            return 2
        if record.score <= -6:
            return -3
        if record.score <= -2:
            return -2
        return 0

    @classmethod
    def _cross_aspect_score(cls, aspect_type: str, hard_penalty: int = 2) -> int:
        if aspect_type in {"Conjunction", "Trine"}:
            return 2
        if aspect_type == "Sextile":
            return 1
        if aspect_type in {"Square", "Opposition"}:
            return -hard_penalty
        return 0

    @classmethod
    def _find_house_ruler_record(cls, chart: NatalTechnicalChart, house_number: int):
        context = chart.traditional_context
        if not context:
            return None
        return next((record for record in context.house_rulers if record.house_number == house_number), None)

    @classmethod
    def _house_ruler_planet(cls, chart: NatalTechnicalChart, house_number: int):
        record = cls._find_house_ruler_record(chart, house_number)
        if not record:
            return None
        return cls._planet_lookup(chart, record.ruler)

    @staticmethod
    def _topic_guidance(key: str) -> Tuple[str, str, str]:
        guidance = {
            "partnership_agreements": (
                "Name the actual agreement each person believes exists here.",
                "Do not let chemistry stand in for commitment, terms, or clarity.",
                "Write down one promise and one boundary clearly.",
            ),
            "attraction_intimacy": (
                "Talk about pace, desire, touch, and access before pressure builds.",
                "Do not confuse intensity with mutual readiness.",
                "Each person names one yes, one no, and one slow-down signal.",
            ),
            "communication_alliance": (
                "Use the strongest communication window deliberately instead of waiting for misunderstanding.",
                "Do not assume shared meaning just because the bond feels close.",
                "Schedule one clarifying conversation with one hard question on the table.",
            ),
            "home_foundation": (
                "Discuss care, family pressure, privacy, and domestic expectations explicitly.",
                "Do not let old family reflexes write the rules of the bond.",
                "Name what helps each person feel safe, rested, and respected in shared space.",
            ),
            "shared_work_direction": (
                "Say what this relationship is building, not only what it is feeling.",
                "Do not turn a bond with different public aims into a silent power contest.",
                "Write one paragraph on what the relationship is for in this season of life.",
            ),
        }
        return guidance.get(
            key,
            (
                "Name the topic plainly before arguing about the whole relationship.",
                "Do not force a single story onto a mixed topic.",
                "Write down what the bond is asking from each person right now.",
            ),
        )

    @classmethod
    def _relationship_lot_names(cls, config: Dict) -> List[str]:
        if config.get("relationship_lots"):
            return list(config["relationship_lots"])
        if config.get("lot"):
            return [config["lot"]]
        return []

    @classmethod
    def _topic_carriers(cls, chart: NatalTechnicalChart, config: Dict) -> List[str]:
        carriers = {
            ruler.id
            for ruler in (cls._house_ruler_planet(chart, house_number) for house_number in config["house_numbers"])
            if ruler
        }
        return sorted(carriers)

    @classmethod
    def _topic_lot_rulers(cls, chart: NatalTechnicalChart, config: Dict) -> List[str]:
        rulers = set()
        for lot_name in cls._relationship_lot_names(config):
            lot = NatalInterpretationService._lot_from_name(chart, lot_name)
            if lot and lot.ruler:
                rulers.add(lot.ruler)
        return sorted(rulers)

    @classmethod
    def _topic_cross_house_witness_evidence(
        cls,
        primary_profile: BirthProfile,
        secondary_profile: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        primary_annual_profection: Optional[AnnualProfectionRecord],
        secondary_annual_profection: Optional[AnnualProfectionRecord],
        config: Dict,
        ontology: Dict,
    ) -> Tuple[int, List[EvidenceItem], int, int]:
        score = 0
        evidence_items: List[EvidenceItem] = []
        positive_links = 0
        negative_links = 0
        helper_planets = set(config.get("helper_planets", []))
        primary_lot_rulers = set(cls._topic_lot_rulers(primary_chart, config))
        secondary_lot_rulers = set(cls._topic_lot_rulers(secondary_chart, config))
        candidates: List[Dict[str, object]] = []

        for host_profile, host_chart, guest_profile, guest_chart, guest_year_lord, guest_lot_rulers in [
            (
                primary_profile,
                primary_chart,
                secondary_profile,
                secondary_chart,
                secondary_annual_profection.lord_of_year if secondary_annual_profection else None,
                secondary_lot_rulers,
            ),
            (
                secondary_profile,
                secondary_chart,
                primary_profile,
                primary_chart,
                primary_annual_profection.lord_of_year if primary_annual_profection else None,
                primary_lot_rulers,
            ),
        ]:
            for house_number in config["house_numbers"]:
                house_sign = NatalInterpretationService._house_sign(host_chart, house_number)
                if not house_sign:
                    continue
                house_title = cls._house_title_for_id(ontology, cls._house_id_from_number(house_number))
                for planet in guest_chart.planets:
                    relation = cls._sign_relation(planet.sign, house_sign)
                    if not relation:
                        continue
                    focus_weight = 0
                    if planet.id in helper_planets:
                        focus_weight += 1
                    if planet.id == guest_year_lord:
                        focus_weight += 1
                    if planet.id in guest_lot_rulers:
                        focus_weight += 1
                    if planet.id in cls.BENEFICS or planet.id in cls.MALEFICS:
                        focus_weight += 1
                    if focus_weight == 0:
                        continue
                    candidate_score = NatalInterpretationService._witness_score(planet, relation)
                    if planet.id in helper_planets:
                        if relation in {"Conjunction", "Trine", "Sextile"}:
                            candidate_score += 1
                        elif relation in {"Square", "Opposition"}:
                            candidate_score -= 1
                    if planet.id == guest_year_lord:
                        candidate_score += 1 if relation in {"Conjunction", "Trine", "Sextile"} else -1 if relation in {"Square", "Opposition"} else 0
                    if planet.id in guest_lot_rulers:
                        candidate_score += 1 if relation in {"Conjunction", "Trine", "Sextile"} else -1 if relation in {"Square", "Opposition"} else 0
                    superior = cls._is_superior_witness(planet.sign, house_sign)
                    if superior and candidate_score > 0:
                        candidate_score += 1
                    elif superior and candidate_score < 0:
                        candidate_score -= 1
                    if candidate_score == 0:
                        continue
                    candidates.append(
                        {
                            "host_name": host_profile.name,
                            "guest_name": guest_profile.name,
                            "planet": planet,
                            "relation": relation,
                            "house_title": house_title,
                            "superior": superior,
                            "score": candidate_score,
                            "focus_weight": focus_weight,
                        }
                    )

        positive_candidates = [candidate for candidate in candidates if candidate["score"] > 0]
        negative_candidates = [candidate for candidate in candidates if candidate["score"] < 0]

        if positive_candidates:
            best_positive = sorted(
                positive_candidates,
                key=lambda candidate: (
                    -int(candidate["score"]),
                    -int(candidate["focus_weight"]),
                    candidate["planet"].id,
                ),
            )[0]
            positive_score = int(best_positive["score"])
            score += positive_score
            positive_links += 1
            positive_planet = best_positive["planet"]
            positive_rule_bits = []
            if positive_planet.id in helper_planets:
                positive_rule_bits.append("a helper planet for this topic")
            if positive_planet.id in {primary_annual_profection.lord_of_year if primary_annual_profection else None, secondary_annual_profection.lord_of_year if secondary_annual_profection else None}:
                positive_rule_bits.append("a current year lord")
            if positive_planet.id in primary_lot_rulers or positive_planet.id in secondary_lot_rulers:
                positive_rule_bits.append("a relevant lot ruler")
            positive_rule_text = ", ".join(positive_rule_bits)
            evidence_items.append(
                cls._evidence_item(
                    observation=(
                        f"{best_positive['guest_name']}'s {positive_planet.id} witnesses {best_positive['host_name']}'s {best_positive['house_title']}"
                        f" by {str(best_positive['relation']).lower()}"
                        + (" from the superior side." if best_positive["superior"] else ".")
                    ),
                    rule=(
                        "In synastry, the other person's planets matter more when they can actually witness the house carrying the topic."
                        + (f" Here the witness is also {positive_rule_text}." if positive_rule_text else "")
                    ),
                    interpretation="The bond receives direct support at the house level instead of relying only on abstract chemistry or ruler-to-ruler contact.",
                    score=positive_score,
                )
            )

        if negative_candidates:
            strongest_negative = sorted(
                negative_candidates,
                key=lambda candidate: (
                    int(candidate["score"]),
                    -int(candidate["focus_weight"]),
                    candidate["planet"].id,
                ),
            )[0]
            negative_score = int(strongest_negative["score"])
            score += negative_score
            negative_links += 1
            negative_planet = strongest_negative["planet"]
            negative_rule_bits = []
            if negative_planet.id in helper_planets:
                negative_rule_bits.append("a helper planet for this topic")
            if negative_planet.id in {primary_annual_profection.lord_of_year if primary_annual_profection else None, secondary_annual_profection.lord_of_year if secondary_annual_profection else None}:
                negative_rule_bits.append("a current year lord")
            if negative_planet.id in primary_lot_rulers or negative_planet.id in secondary_lot_rulers:
                negative_rule_bits.append("a relevant lot ruler")
            negative_rule_text = ", ".join(negative_rule_bits)
            evidence_items.append(
                cls._evidence_item(
                    observation=(
                        f"{strongest_negative['guest_name']}'s {negative_planet.id} presses {strongest_negative['host_name']}'s {strongest_negative['house_title']}"
                        f" by {str(strongest_negative['relation']).lower()}"
                        + (" from the superior side." if strongest_negative["superior"] else ".")
                    ),
                    rule=(
                        "House-level pressure becomes more concrete when the other person's planet can directly witness the topic house."
                        + (f" Here the witness is also {negative_rule_text}." if negative_rule_text else "")
                    ),
                    interpretation="The relationship topic is being stressed at the house level, so practical handling matters as much as emotional tone.",
                    score=negative_score,
                    caveat="A pressured house witness can still produce honesty, urgency, or necessary reality-testing.",
                )
            )

        if len([candidate for candidate in positive_candidates if int(candidate["score"]) >= 2]) >= 2:
            score += 1
            positive_links += 1
            evidence_items.append(
                cls._evidence_item(
                    observation="More than one cross-chart witness supports these houses directly.",
                    rule="Repeated direct witness at the house level strengthens the topic beyond one lucky contact.",
                    interpretation="Support for this topic is repeating through more than one doorway in the bond.",
                    score=1,
                )
            )
        if len([candidate for candidate in negative_candidates if int(candidate["score"]) <= -2]) >= 2:
            score -= 1
            negative_links += 1
            evidence_items.append(
                cls._evidence_item(
                    observation="More than one cross-chart witness presses these houses directly.",
                    rule="Repeated difficult witness makes a relationship topic louder and harder to ignore.",
                    interpretation="This topic is not only carrying one sharp contact; the pressure repeats through the house structure itself.",
                    score=-1,
                    caveat="Repeated pressure should be translated into pacing and boundary work, not fatalism.",
                )
            )

        return score, evidence_items, positive_links, negative_links

    @classmethod
    def _topic_lot_bridge_evidence(
        cls,
        primary_profile: BirthProfile,
        secondary_profile: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        config: Dict,
    ) -> Tuple[int, List[EvidenceItem], int, int]:
        score = 0
        evidence_items: List[EvidenceItem] = []
        positive_links = 0
        negative_links = 0
        lot_names = cls._relationship_lot_names(config)
        primary_carriers = set(cls._topic_carriers(primary_chart, config))
        secondary_carriers = set(cls._topic_carriers(secondary_chart, config))

        for lot_name in lot_names:
            primary_lot = NatalInterpretationService._lot_from_name(primary_chart, lot_name)
            secondary_lot = NatalInterpretationService._lot_from_name(secondary_chart, lot_name)
            if not primary_lot or not secondary_lot:
                continue
            primary_in_topic = (
                (primary_lot.house and cls._house_number(primary_lot.house) in config["house_numbers"])
                or primary_lot.ruler in primary_carriers
            )
            secondary_in_topic = (
                (secondary_lot.house and cls._house_number(secondary_lot.house) in config["house_numbers"])
                or secondary_lot.ruler in secondary_carriers
            )
            lot_meaning = "circumstance and embodiment" if lot_name == "Fortune" else "intention and chosen direction"
            if primary_in_topic and secondary_in_topic:
                score += 2
                positive_links += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"Both {primary_profile.name}'s and {secondary_profile.name}'s {lot_name} turn toward {config['title'].lower()}.",
                        rule=f"{lot_name} refines relationship topics by showing where {lot_meaning} concentrates in each chart.",
                        interpretation=f"This topic is being reinforced by both charts through {lot_meaning}.",
                        score=2,
                    )
                )
            elif primary_in_topic or secondary_in_topic:
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"{primary_profile.name}'s {lot_name} {'does' if primary_in_topic else 'does not'} emphasize this topic, "
                            f"while {secondary_profile.name}'s {lot_name} {'does' if secondary_in_topic else 'does not'}."
                        ),
                        rule=f"{lot_name} shows whether a relationship topic arrives more through {lot_meaning} for one person than the other.",
                        interpretation=(
                            f"This topic is weighted more by {lot_meaning} for one person, so the bond may not experience it symmetrically."
                        ),
                        score=0,
                        caveat="Asymmetry in Fortune or Spirit does not block the relationship; it changes how each person meets the topic.",
                    )
                )

            lot_ruler_aspect = cls._find_inter_aspect(aspects, primary_lot.ruler, secondary_lot.ruler)
            if lot_ruler_aspect:
                lot_aspect_score = cls._cross_aspect_score(lot_ruler_aspect.type, 1 if lot_name == "Fortune" else 2)
                score += lot_aspect_score
                if lot_aspect_score > 0:
                    positive_links += 1
                elif lot_aspect_score < 0:
                    negative_links += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"The rulers of {primary_profile.name}'s and {secondary_profile.name}'s {lot_name} connect by {lot_ruler_aspect.type.lower()}."
                        ),
                        rule=f"Contacts between {lot_name} rulers show whether the same layer of {lot_meaning} can cooperate across the bond.",
                        interpretation=(
                            f"The {lot_name} layer of this topic is easier to share across the relationship."
                            if lot_aspect_score > 0 else
                            f"The {lot_name} layer of this topic is active, but it arrives with friction or mismatched pacing."
                        ),
                        score=lot_aspect_score,
                        caveat=(
                            "A hard lot-ruler contact can still create a strong bond; it often makes the topic harder to carry cleanly."
                            if lot_aspect_score < 0 else None
                        ),
                    )
                )

        return score, evidence_items, positive_links, negative_links

    @classmethod
    def _topic_priority_tuple(
        cls,
        record: TopicJudgmentRecord,
        config: Dict,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        primary_annual_profection: Optional[AnnualProfectionRecord],
        secondary_annual_profection: Optional[AnnualProfectionRecord],
        primary_solar_return: Optional[SolarReturnRecord],
        secondary_solar_return: Optional[SolarReturnRecord],
    ) -> Tuple[int, int, int, int, int, str]:
        relevant_house_ids = {cls._house_id_from_number(house_number) for house_number in config["house_numbers"]}
        activation_priority = 0
        for annual_profection in [primary_annual_profection, secondary_annual_profection]:
            if not annual_profection:
                continue
            if annual_profection.activated_house in config["house_numbers"]:
                activation_priority += 2
            if annual_profection.lord_of_year_house in relevant_house_ids:
                activation_priority += 1
        for solar_return in [primary_solar_return, secondary_solar_return]:
            if not solar_return:
                continue
            if solar_return.year_lord_house in relevant_house_ids:
                activation_priority += 1
            if solar_return.sun_house in relevant_house_ids:
                activation_priority += 1

        lot_priority = 0
        for chart in [primary_chart, secondary_chart]:
            carriers = set(cls._topic_carriers(chart, config))
            for lot_name in cls._relationship_lot_names(config):
                lot = NatalInterpretationService._lot_from_name(chart, lot_name)
                if not lot:
                    continue
                if lot.house and cls._house_number(lot.house) in config["house_numbers"]:
                    lot_priority += 2
                elif lot.ruler in carriers:
                    lot_priority += 1

        confidence_rank = {"high": 2, "medium": 1, "low": 0}.get(record.confidence, 0)
        priority_bias = int(config.get("priority_bias", 0))
        return (-abs(record.score), -activation_priority, -lot_priority, -confidence_rank, -priority_bias, record.title)

    @classmethod
    def _planet_condition_phrase(cls, planet) -> str:
        if not planet:
            return "condition unavailable"
        parts: List[str] = []
        if planet.traditional_strength:
            parts.append(planet.traditional_strength)
        if planet.house_condition:
            parts.append(planet.house_condition)
        if planet.sect_status == "in_sect":
            parts.append("in sect")
        elif planet.sect_status == "contrary_to_sect":
            parts.append("contrary to sect")
        if "domicile" in planet.essential_dignities:
            parts.append("in domicile")
        elif "exaltation" in planet.essential_dignities:
            parts.append("in exaltation")
        elif "triplicity" in planet.essential_dignities:
            parts.append("holding triplicity dignity")
        if planet.visibility_status in {"combust", "under_beams", "cazimi"}:
            parts.append(planet.visibility_status.replace("_", " "))
        return ", ".join(parts[:4]) if parts else "mixed"

    @classmethod
    def _find_inter_aspect(
        cls,
        aspects: List[SynastryAspectRecord],
        primary_planet: Optional[str],
        secondary_planet: Optional[str],
    ) -> Optional[SynastryAspectRecord]:
        if not primary_planet or not secondary_planet:
            return None
        return next(
            (
                aspect for aspect in aspects
                if aspect.first == primary_planet and aspect.second == secondary_planet
            ),
            None,
        )

    @classmethod
    def _activation_summary_bits(
        cls,
        profile: BirthProfile,
        chart: NatalTechnicalChart,
        annual_profection: Optional[AnnualProfectionRecord],
        solar_return: Optional[SolarReturnRecord],
        ontology: Dict,
    ) -> Dict[str, str]:
        context = chart.traditional_context
        asc_ruler = cls._planet_lookup(chart, context.ascendant_ruler) if context and context.ascendant_ruler else None
        year_lord = cls._planet_lookup(chart, annual_profection.lord_of_year) if annual_profection else None
        activated_topics = cls._house_topics_for_number(ontology, annual_profection.activated_house if annual_profection else None)
        solar_return_clause = ""
        if solar_return:
            solar_return_clause = (
                f"The solar return rises in {solar_return.return_ascendant_sign} and places the year lord in {cls._house_title_for_id(ontology, solar_return.year_lord_house)}"
                + (f", where it is {solar_return.year_lord_strength}." if solar_return.year_lord else ".")
            )
        return {
            "profile_name": profile.name,
            "ascendant_sign": context.ascendant_sign if context else "unknown",
            "ascendant_ruler": context.ascendant_ruler if context else "unknown",
            "ascendant_ruler_condition": cls._planet_condition_phrase(asc_ruler),
            "ascendant_ruler_house": cls._house_title_for_id(ontology, asc_ruler.house if asc_ruler else None),
            "activated_house": cls._house_title_for_id(ontology, cls._house_id_from_number(annual_profection.activated_house)) if annual_profection else "current house",
            "activated_topics": activated_topics,
            "year_lord": annual_profection.lord_of_year if annual_profection else "unknown",
            "year_lord_condition": cls._planet_condition_phrase(year_lord),
            "year_lord_house": cls._house_title_for_id(ontology, annual_profection.lord_of_year_house if annual_profection else None),
            "solar_return_clause": solar_return_clause,
        }

    @classmethod
    def _year_lord_bridge_summary(
        cls,
        primary_profile: BirthProfile,
        secondary_profile: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        primary_annual_profection: Optional[AnnualProfectionRecord],
        secondary_annual_profection: Optional[AnnualProfectionRecord],
        primary_solar_return: Optional[SolarReturnRecord],
        secondary_solar_return: Optional[SolarReturnRecord],
        aspects: List[SynastryAspectRecord],
        ontology: Dict,
    ) -> Dict[str, str]:
        primary_bits = cls._activation_summary_bits(primary_profile, primary_chart, primary_annual_profection, primary_solar_return, ontology)
        secondary_bits = cls._activation_summary_bits(secondary_profile, secondary_chart, secondary_annual_profection, secondary_solar_return, ontology)
        lord_aspect = cls._find_inter_aspect(
            aspects,
            primary_annual_profection.lord_of_year if primary_annual_profection else None,
            secondary_annual_profection.lord_of_year if secondary_annual_profection else None,
        )
        tone = "parallel but separate"
        bridge_sentence = (
            f"{primary_profile.name}'s year centers {primary_bits['activated_topics']}, while {secondary_profile.name}'s year centers {secondary_bits['activated_topics']}."
        )
        if lord_aspect:
            if lord_aspect.type in {"Trine", "Sextile", "Conjunction"}:
                tone = "cooperative"
            elif lord_aspect.type in {"Square", "Opposition"}:
                tone = "demanding"
            bridge_sentence += (
                f" The year lords connect by {lord_aspect.type.lower()}, so the bond currently carries a {tone} link between those two storylines."
            )
        else:
            bridge_sentence += (
                " The year lords do not directly aspect each other, so the relationship should be read through two concurrent personal activations before assuming one shared agenda."
            )

        if primary_solar_return and secondary_solar_return:
            bridge_sentence += (
                f" The current solar returns rise in {primary_solar_return.return_ascendant_sign} for {primary_profile.name} and {secondary_solar_return.return_ascendant_sign} for {secondary_profile.name}, which shows how differently each person is carrying the year."
            )

        return {
            "tone": tone,
            "bridge_sentence": bridge_sentence,
            "lord_aspect_type": lord_aspect.type if lord_aspect else "",
        }

    @classmethod
    def _find_pair_aspect(
        cls,
        aspects: List[SynastryAspectRecord],
        primary_planet: str,
        secondary_planet: str,
    ) -> Optional[SynastryAspectRecord]:
        return next(
            (
                aspect for aspect in aspects
                if aspect.first == primary_planet and aspect.second == secondary_planet
            ),
            None,
        )

    @classmethod
    def _best_bridge_aspect(
        cls,
        aspects: List[SynastryAspectRecord],
        pairs: List[Tuple[str, str]],
    ) -> Optional[Tuple[SynastryAspectRecord, str, str]]:
        matches: List[Tuple[SynastryAspectRecord, str, str]] = []
        for primary_planet, secondary_planet in pairs:
            match = cls._find_pair_aspect(aspects, primary_planet, secondary_planet)
            if match:
                matches.append((match, primary_planet, secondary_planet))
        if not matches:
            return None
        return sorted(matches, key=lambda item: (item[0].orb, -abs(cls._cross_aspect_score(item[0].type)), item[0].type))[0]

    @classmethod
    def _topic_activation_evidence(
        cls,
        profile: BirthProfile,
        annual_profection: Optional[AnnualProfectionRecord],
        solar_return: Optional[SolarReturnRecord],
        config: Dict,
        carrier_planets: List[str],
    ) -> Tuple[int, List[EvidenceItem]]:
        score = 0
        evidence_items: List[EvidenceItem] = []
        relevant_house_ids = {cls._house_id_from_number(house_number) for house_number in config["house_numbers"]}
        topic_title = config["title"].lower()
        helper_planets = set(config.get("helper_planets", []))
        carrier_set = set(carrier_planets)

        if annual_profection:
            if annual_profection.activated_house in config["house_numbers"]:
                score += 2
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"{profile.name}'s current profection activates House {annual_profection.activated_house} for {topic_title}."
                        ),
                        rule="When the profection year lands on a relevant house, that relationship topic becomes live rather than theoretical.",
                        interpretation=f"{profile.name} is bringing fresh yearly emphasis into this part of the bond.",
                        score=2,
                    )
                )
            if annual_profection.lord_of_year in carrier_set or annual_profection.lord_of_year in helper_planets:
                score += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"{profile.name}'s year lord is {annual_profection.lord_of_year}, one of this topic's carriers.",
                        rule="A topic intensifies when the lord of the year is also one of its rulers or helper planets.",
                        interpretation=f"{profile.name} is not entering this topic neutrally; the year itself is pushing it forward.",
                        score=1,
                    )
                )
            if annual_profection.lord_of_year_house in relevant_house_ids:
                score += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"{profile.name}'s year lord is placed in {annual_profection.lord_of_year_house}.",
                        rule="A year lord placed in a relevant house puts concrete attention on that topic.",
                        interpretation=f"{profile.name}'s current year keeps landing back on this relationship area.",
                        score=1,
                    )
                )

        if solar_return:
            if solar_return.year_lord_house in relevant_house_ids:
                score += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"{profile.name}'s solar return places the year lord in {solar_return.year_lord_house}.",
                        rule="Solar return placement refines where the profection year is concentrating its effort.",
                        interpretation=f"The yearly return doubles down on this relationship topic for {profile.name}.",
                        score=1,
                    )
                )
            if solar_return.sun_house in relevant_house_ids:
                score += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"{profile.name}'s solar return Sun falls in {solar_return.sun_house}.",
                        rule="The solar return Sun shows where the year becomes most visible and enacted.",
                        interpretation=f"{profile.name} is likely to experience this topic openly in the present year.",
                        score=1,
                    )
                )

        return score, evidence_items

    @classmethod
    def _topic_judgment_data(
        cls,
        primary_profile: BirthProfile,
        secondary_profile: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        primary_annual_profection: Optional[AnnualProfectionRecord],
        secondary_annual_profection: Optional[AnnualProfectionRecord],
        primary_solar_return: Optional[SolarReturnRecord],
        secondary_solar_return: Optional[SolarReturnRecord],
        ontology: Dict,
        config: Dict,
    ) -> TopicJudgmentRecord:
        primary_topic = NatalInterpretationService._topic_judgment_data(primary_chart, ontology, config)
        secondary_topic = NatalInterpretationService._topic_judgment_data(secondary_chart, ontology, config)
        score = 0
        evidence_items: List[EvidenceItem] = []
        citations = set(primary_topic.citations + secondary_topic.citations)
        positive_links = 0
        negative_links = 0

        primary_base = cls._topic_record_score(primary_topic)
        secondary_base = cls._topic_record_score(secondary_topic)
        score += primary_base + secondary_base

        primary_anchor = primary_topic.evidence_items[0].observation if primary_topic.evidence_items else f"{primary_profile.name} has {primary_topic.classification} testimony in {config['title'].lower()}."
        secondary_anchor = secondary_topic.evidence_items[0].observation if secondary_topic.evidence_items else f"{secondary_profile.name} has {secondary_topic.classification} testimony in {config['title'].lower()}."

        evidence_items.append(
            cls._evidence_item(
                observation=f"{primary_profile.name}: {primary_anchor}",
                rule="Traditional synastry begins with each person's natal condition in the topic before judging the bond between them.",
                interpretation=(
                    f"{primary_profile.name} enters {config['title'].lower()} with {primary_topic.classification} natal testimony at {primary_topic.confidence} confidence."
                ),
                score=primary_base,
                caveat=(
                    "A strained natal topic can still be steadied if the other chart and the current year provide usable support."
                    if primary_base < 0 else None
                ),
            )
        )
        evidence_items.append(
            cls._evidence_item(
                observation=f"{secondary_profile.name}: {secondary_anchor}",
                rule="Relationship topics are carried by two natal structures at once, not by one chart alone.",
                interpretation=(
                    f"{secondary_profile.name} enters {config['title'].lower()} with {secondary_topic.classification} natal testimony at {secondary_topic.confidence} confidence."
                ),
                score=secondary_base,
                caveat=(
                    "A supportive natal topic still needs real contact and timing to become visible in the relationship."
                    if secondary_base > 0 else None
                ),
            )
        )

        primary_carriers = cls._topic_carriers(primary_chart, config)
        secondary_carriers = cls._topic_carriers(secondary_chart, config)

        primary_activation_score, primary_activation_items = cls._topic_activation_evidence(
            primary_profile,
            primary_annual_profection,
            primary_solar_return,
            config,
            primary_carriers,
        )
        secondary_activation_score, secondary_activation_items = cls._topic_activation_evidence(
            secondary_profile,
            secondary_annual_profection,
            secondary_solar_return,
            config,
            secondary_carriers,
        )
        score += primary_activation_score + secondary_activation_score
        evidence_items.extend(primary_activation_items[:2])
        evidence_items.extend(secondary_activation_items[:2])
        if primary_activation_items or secondary_activation_items:
            citations.update(cls._resolve_labels(["traditional_annual_profection", "traditional_solar_return"]))
        if primary_activation_score > 0:
            positive_links += 1
        if secondary_activation_score > 0:
            positive_links += 1

        if (
            primary_annual_profection
            and secondary_annual_profection
            and primary_annual_profection.activated_house in config["house_numbers"]
            and secondary_annual_profection.activated_house in config["house_numbers"]
        ):
            score += 1
            positive_links += 1
            evidence_items.append(
                cls._evidence_item(
                    observation=(
                        f"Both profection years currently activate {config['title'].lower()}."
                    ),
                    rule="When the same topic is live for both people at once, the relationship feels that topic more immediately.",
                    interpretation="The bond is carrying shared timing pressure here, not only abstract compatibility.",
                    score=1,
                )
            )
            citations.update(cls._resolve_labels(["traditional_annual_profection"]))

        house_witness_score, house_witness_items, house_positive_links, house_negative_links = cls._topic_cross_house_witness_evidence(
            primary_profile,
            secondary_profile,
            primary_chart,
            secondary_chart,
            primary_annual_profection,
            secondary_annual_profection,
            config,
            ontology,
        )
        score += house_witness_score
        evidence_items.extend(house_witness_items)
        positive_links += house_positive_links
        negative_links += house_negative_links
        if house_witness_items:
            citations.update(cls._resolve_labels(["traditional_aversion_witness", "traditional_overcoming"]))

        ruler_links: List[Tuple[int, SynastryAspectRecord, str]] = []
        for house_number in config["house_numbers"]:
            house_title = cls._house_title_for_id(ontology, cls._house_id_from_number(house_number))
            primary_ruler = cls._house_ruler_planet(primary_chart, house_number)
            secondary_ruler = cls._house_ruler_planet(secondary_chart, house_number)
            if not primary_ruler or not secondary_ruler:
                continue
            aspect = cls._find_inter_aspect(aspects, primary_ruler.id, secondary_ruler.id)
            if aspect:
                ruler_links.append((house_number, aspect, house_title))

        if ruler_links:
            for house_number, aspect, house_title in sorted(ruler_links, key=lambda item: item[1].orb)[:2]:
                primary_ruler = cls._house_ruler_planet(primary_chart, house_number)
                secondary_ruler = cls._house_ruler_planet(secondary_chart, house_number)
                aspect_score = cls._cross_aspect_score(aspect.type, config.get("hard_aspect_penalty", 2))
                score += aspect_score
                if aspect_score > 0:
                    positive_links += 1
                elif aspect_score < 0:
                    negative_links += 1
                superior_note = ""
                if primary_ruler and secondary_ruler:
                    if cls._is_superior_witness(primary_ruler.sign, secondary_ruler.sign):
                        superior_note = f" {primary_profile.name}'s ruler overcomes {secondary_profile.name}'s."
                        citations.update(cls._resolve_labels(["traditional_overcoming"]))
                    elif cls._is_superior_witness(secondary_ruler.sign, primary_ruler.sign):
                        superior_note = f" {secondary_profile.name}'s ruler overcomes {primary_profile.name}'s."
                        citations.update(cls._resolve_labels(["traditional_overcoming"]))
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"{primary_profile.name}'s {primary_ruler.id if primary_ruler else 'topic ruler'} and {secondary_profile.name}'s {secondary_ruler.id if secondary_ruler else 'topic ruler'}"
                            f" connect by {aspect.type.lower()} around {house_title}."
                        ),
                        rule="Traditional synastry judges a relationship topic by the contact between each person's house rulers for that topic.",
                        interpretation=(
                            "The topic passes more directly between the two charts, so it is easier to engage deliberately."
                            if aspect_score > 0 else
                            "The topic is present between the charts, but it tends to arrive with friction, asymmetry, or opposite pacing."
                        ) + superior_note,
                        score=aspect_score,
                        caveat=(
                            "A hard ruler contact can create seriousness and loyalty as well as strain."
                            if aspect_score < 0 else None
                        ),
                    )
                )
            citations.update(cls._resolve_labels(["tetrabiblos_aspect_relation", "tetrabiblos_house_topic"]))
        elif primary_base < 0 or secondary_base < 0:
            score -= 1
            negative_links += 1
            evidence_items.append(
                cls._evidence_item(
                    observation=f"The main house rulers for {config['title'].lower()} do not directly connect across the two charts.",
                    rule="When strained topics lack a direct ruler bridge, the bond has to work harder to coordinate them.",
                    interpretation="The relationship may carry parallel needs in this area without an easy built-in handoff between the two people.",
                    score=-1,
                    caveat="Absence of a direct ruler aspect qualifies the topic; it does not make connection impossible.",
                )
            )
            citations.update(cls._resolve_labels(["traditional_aversion_witness"]))

        bridge_aspect = cls._best_bridge_aspect(aspects, config.get("bridge_pairs", []))
        if bridge_aspect:
            aspect, primary_planet, secondary_planet = bridge_aspect
            helper_score = cls._cross_aspect_score(aspect.type, config.get("hard_aspect_penalty", 2))
            score += helper_score
            if helper_score > 0:
                positive_links += 1
            elif helper_score < 0:
                negative_links += 1
            evidence_items.append(
                cls._evidence_item(
                    observation=(
                        f"{primary_profile.name}'s {primary_planet} connects with {secondary_profile.name}'s {secondary_planet} by {aspect.type.lower()}."
                    ),
                    rule="Helper planets show the style through which a relationship topic is likely to be expressed or negotiated.",
                    interpretation=(
                        "The bond has a more usable channel for this topic's style, tone, or chemistry."
                        if helper_score > 0 else
                        "The bond keeps touching this topic through heat, pressure, or mixed timing rather than easy flow."
                    ),
                    score=helper_score,
                    caveat=(
                        "Hard helper contacts can intensify attraction or honesty even when they also create strain."
                        if helper_score < 0 else None
                    ),
                )
            )
            citations.update(cls._resolve_labels(["tetrabiblos_aspect_relation"]))

        if primary_annual_profection and secondary_carriers:
            outward_year_hit = next(
                (
                    aspect for aspect in aspects
                    if aspect.first == primary_annual_profection.lord_of_year and aspect.second in secondary_carriers
                ),
                None,
            )
            if outward_year_hit:
                year_score = cls._cross_aspect_score(outward_year_hit.type, 1)
                score += year_score
                if year_score > 0:
                    positive_links += 1
                elif year_score < 0:
                    negative_links += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"{primary_profile.name}'s year lord {primary_annual_profection.lord_of_year} aspects one of {secondary_profile.name}'s topic rulers by {outward_year_hit.type.lower()}."
                        ),
                        rule="A year lord contacting the other person's topic ruler shows the current year pushing directly into the relationship topic.",
                        interpretation=(
                            f"{primary_profile.name}'s present-year storyline is actively entering {secondary_profile.name}'s side of this topic."
                        ),
                        score=year_score,
                    )
                )
                citations.update(cls._resolve_labels(["traditional_annual_profection", "tetrabiblos_aspect_relation"]))

        if secondary_annual_profection and primary_carriers:
            inward_year_hit = next(
                (
                    aspect for aspect in aspects
                    if aspect.first in primary_carriers and aspect.second == secondary_annual_profection.lord_of_year
                ),
                None,
            )
            if inward_year_hit:
                year_score = cls._cross_aspect_score(inward_year_hit.type, 1)
                score += year_score
                if year_score > 0:
                    positive_links += 1
                elif year_score < 0:
                    negative_links += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"{secondary_profile.name}'s year lord {secondary_annual_profection.lord_of_year} is contacted by one of {primary_profile.name}'s topic rulers via {inward_year_hit.type.lower()}."
                        ),
                        rule="The reverse year-lord contact shows the topic being pushed from the other side of the bond as well.",
                        interpretation=(
                            f"{secondary_profile.name}'s present-year storyline is also landing directly in this part of the relationship."
                        ),
                        score=year_score,
                    )
                )
                citations.update(cls._resolve_labels(["traditional_annual_profection", "tetrabiblos_aspect_relation"]))

        lot_bridge_score, lot_bridge_items, lot_positive_links, lot_negative_links = cls._topic_lot_bridge_evidence(
            primary_profile,
            secondary_profile,
            primary_chart,
            secondary_chart,
            aspects,
            config,
        )
        score += lot_bridge_score
        evidence_items.extend(lot_bridge_items)
        positive_links += lot_positive_links
        negative_links += lot_negative_links
        if lot_bridge_items:
            citations.update(cls._resolve_labels(["traditional_fortune_spirit", "tetrabiblos_aspect_relation"]))

        strained_topic = primary_base < 0 or secondary_base < 0
        if positive_links >= 2 and strained_topic:
            score += 1
            evidence_items.append(
                cls._evidence_item(
                    observation="Supportive timing or bridge factors repeat around a topic that is not easy in both charts.",
                    rule="Bonification happens when usable support reaches a topic that would otherwise be harder to carry.",
                    interpretation="This topic is not effortless, but it is more workable than the strained natal testimony alone would imply.",
                    score=1,
                )
            )
            citations.update(cls._resolve_labels(["traditional_maltreatment_bonification"]))
        if negative_links >= 2 and strained_topic:
            score -= 1
            evidence_items.append(
                cls._evidence_item(
                    observation="Repeated hard links are landing on a topic that already carries strain in at least one chart.",
                    rule="Maltreatment grows when difficult contacts keep landing on an already pressured significator or topic area.",
                    interpretation="This part of the relationship needs pacing, explicit agreements, and more conscious handling than the rest of the bond.",
                    score=-1,
                    caveat="Difficult testimony should be communicated as strain or vulnerability, not fatal certainty.",
                )
            )
            citations.update(cls._resolve_labels(["traditional_maltreatment_bonification"]))

        classification = cls._topic_score_bucket(score)
        confidence = cls._confidence_label(len(evidence_items), score)
        return TopicJudgmentRecord(
            key=config["key"],
            title=config["title"],
            score=score,
            classification=classification,
            confidence=confidence,
            relevant_houses=list(config["house_numbers"]),
            relevant_lot=config.get("lot"),
            evidence_items=evidence_items,
            citations=sorted(citations),
        )

    @classmethod
    def build_topic_judgments(
        cls,
        primary_profile: BirthProfile,
        secondary_profile: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        primary_annual_profection: Optional[AnnualProfectionRecord],
        secondary_annual_profection: Optional[AnnualProfectionRecord],
        primary_solar_return: Optional[SolarReturnRecord],
        secondary_solar_return: Optional[SolarReturnRecord],
        ontology: Dict,
    ) -> List[TopicJudgmentRecord]:
        config_by_key = {config["key"]: config for config in cls.TOPIC_CONFIGS}
        judgments = [
            cls._topic_judgment_data(
                primary_profile,
                secondary_profile,
                primary_chart,
                secondary_chart,
                aspects,
                primary_annual_profection,
                secondary_annual_profection,
                primary_solar_return,
                secondary_solar_return,
                ontology,
                config,
            )
            for config in cls.TOPIC_CONFIGS
        ]
        return sorted(
            judgments,
            key=lambda record: cls._topic_priority_tuple(
                record,
                config_by_key[record.key],
                primary_chart,
                secondary_chart,
                primary_annual_profection,
                secondary_annual_profection,
                primary_solar_return,
                secondary_solar_return,
            ),
        )

    @classmethod
    def _featured_topic_judgments(cls, topic_judgments: List[TopicJudgmentRecord]) -> List[TopicJudgmentRecord]:
        return topic_judgments[:3]

    @classmethod
    def _build_topic_judgment_blocks(cls, topic_judgments: List[TopicJudgmentRecord]) -> List[InterpretationBlock]:
        blocks: List[InterpretationBlock] = []
        for record in cls._featured_topic_judgments(topic_judgments):
            sentences = [
                f"{record.title} shows {record.classification} testimony with {record.confidence} confidence."
            ]
            for item in record.evidence_items[:3]:
                interpretation = item.interpretation.strip()
                if not interpretation.endswith("."):
                    interpretation += "."
                sentences.append(interpretation[:1].upper() + interpretation[1:])
            blocks.append(
                InterpretationBlock(
                    title=record.title,
                    summary=" ".join(sentences),
                    citations=record.citations,
                    block_type="synastry_topic_judgment",
                    topic_key=record.key,
                    confidence=record.confidence,
                    evidence_items=record.evidence_items[:6],
                    caveats=[item.caveat for item in record.evidence_items if item.caveat][:3],
                )
            )
        return blocks

    @classmethod
    def _contact_priority(
        cls,
        aspect: SynastryAspectRecord,
        primary_year_lord: Optional[str],
        secondary_year_lord: Optional[str],
    ) -> tuple:
        involvement = 0
        if primary_year_lord and aspect.first == primary_year_lord:
            involvement += 2
        if secondary_year_lord and aspect.second == secondary_year_lord:
            involvement += 2
        if {aspect.first, aspect.second} == {"Sun", "Moon"}:
            involvement += 2
        if {aspect.first, aspect.second} == {"Venus", "Mars"}:
            involvement += 1
        aspect_weight = {"Conjunction": 4, "Opposition": 3, "Square": 3, "Trine": 2, "Sextile": 1}.get(aspect.type, 0)
        return (-involvement, -aspect_weight, aspect.orb)

    @staticmethod
    def _resolve_labels(citation_ids: List[str]) -> List[str]:
        resolved = CitationService.resolve(citation_ids)
        return [item.get("label", item.get("id", "")) for item in resolved]

    @staticmethod
    def _house_number(house_id: str) -> int:
        return int(house_id.replace("House", ""))

    @staticmethod
    def _house_id_from_number(house_number: int) -> str:
        return f"House{house_number}"

    @staticmethod
    def _block(title: str, summary: str, citations: List[str], block_type: str) -> InterpretationBlock:
        return InterpretationBlock(title=title, summary=summary, citations=citations, block_type=block_type)

    @classmethod
    def _angular_difference(cls, first: float, second: float) -> float:
        return AspectPolicyService.angular_difference(first, second)

    @classmethod
    def _build_inter_chart_aspects(cls, primary_chart: NatalTechnicalChart, secondary_chart: NatalTechnicalChart) -> List[SynastryAspectRecord]:
        aspects: List[SynastryAspectRecord] = []
        for primary_planet in primary_chart.planets:
            if primary_planet.id not in cls.INTEREST_PLANETS:
                continue
            for secondary_planet in secondary_chart.planets:
                if secondary_planet.id not in cls.INTEREST_PLANETS:
                    continue
                aspect = AspectPolicyService.detect_aspect(
                    first_body=primary_planet.id,
                    first_longitude=primary_planet.longitude,
                    second_body=secondary_planet.id,
                    second_longitude=secondary_planet.longitude,
                    context="synastry",
                )
                if aspect:
                    aspects.append(
                        SynastryAspectRecord(
                            first_owner="primary",
                            first=primary_planet.id,
                            second_owner="secondary",
                            second=secondary_planet.id,
                            type=aspect.type,
                            degrees=aspect.degrees,
                            orb=aspect.orb,
                        )
                    )
        aspects.sort(key=lambda item: item.orb)
        return aspects

    @staticmethod
    def _levi_lookup(ontology: Dict) -> List[Dict]:
        return ontology.get("levi_currents", [])

    @classmethod
    def _score_levi_current(
        cls,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        current: Dict,
    ) -> int:
        trigger_planets = set(current.get("trigger_planets", []))
        trigger_signs = set(current.get("trigger_signs", []))
        trigger_houses = set(current.get("trigger_houses", []))
        trigger_aspects = set(current.get("trigger_aspects", []))

        score = 0
        for chart in (primary_chart, secondary_chart):
            for planet in chart.planets:
                house_number = cls._house_number(planet.house)
                if planet.sign in trigger_signs:
                    score += 2
                if house_number in trigger_houses:
                    score += 1
                if planet.id in trigger_planets:
                    score += 1
                    if planet.sign in trigger_signs or house_number in trigger_houses:
                        score += 2

        for aspect in aspects[:8]:
            if aspect.type in trigger_aspects:
                score += 2
            if aspect.first in trigger_planets or aspect.second in trigger_planets:
                score += 1

        return score

    @classmethod
    def _select_levi_current(
        cls,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        ontology: Dict,
    ) -> Optional[Dict]:
        currents = cls._levi_lookup(ontology)
        if not currents:
            return None
        return sorted(
            currents,
            key=lambda item: (-cls._score_levi_current(primary_chart, secondary_chart, aspects, item), item.get("display_name", "")),
        )[0]

    @classmethod
    def _current_frame_block(
        cls,
        profile: BirthProfile,
        chart: NatalTechnicalChart,
        annual_profection: Optional[AnnualProfectionRecord],
        solar_return: Optional[SolarReturnRecord],
        ontology: Dict,
        owner_label: str,
    ) -> Optional[InterpretationBlock]:
        if not chart.traditional_context or not annual_profection:
            return None
        bits = cls._activation_summary_bits(profile, chart, annual_profection, solar_return, ontology)
        summary = (
            f"{profile.name} enters the bond through {bits['ascendant_sign']} rising, with {bits['ascendant_ruler']} carrying the natal frame. "
            f"{bits['ascendant_ruler']} is {bits['ascendant_ruler_condition']} in {bits['ascendant_ruler_house']}. "
            f"The current profection activates {bits['activated_house']}, so {bits['activated_topics']} are especially live. "
            f"The year lord is {bits['year_lord']}, which is {bits['year_lord_condition']} in {bits['year_lord_house']}. "
            f"{bits['solar_return_clause'] or 'The yearly return layer is not available yet.'}"
        )
        return cls._block(
            title=f"{owner_label} current natal frame",
            summary=summary,
            citations=cls._resolve_labels([
                "traditional_sect_condition",
                "traditional_annual_profection",
                "traditional_solar_return",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
            ]),
            block_type="synastry_natal_frame",
        )

    @classmethod
    def _yearly_bridge_block(
        cls,
        primary_profile: BirthProfile,
        secondary_profile: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        primary_annual_profection: Optional[AnnualProfectionRecord],
        secondary_annual_profection: Optional[AnnualProfectionRecord],
        primary_solar_return: Optional[SolarReturnRecord],
        secondary_solar_return: Optional[SolarReturnRecord],
        aspects: List[SynastryAspectRecord],
        ontology: Dict,
    ) -> Optional[InterpretationBlock]:
        if not primary_annual_profection or not secondary_annual_profection:
            return None
        bridge = cls._year_lord_bridge_summary(
            primary_profile,
            secondary_profile,
            primary_chart,
            secondary_chart,
            primary_annual_profection,
            secondary_annual_profection,
            primary_solar_return,
            secondary_solar_return,
            aspects,
            ontology,
        )
        return cls._block(
            title="How the current years meet",
            summary=bridge["bridge_sentence"],
            citations=cls._resolve_labels([
                "traditional_annual_profection",
                "traditional_solar_return",
                "tetrabiblos_aspect_relation",
            ]),
            block_type="synastry_yearly_bridge",
        )

    @classmethod
    def _sign_pair_block(cls, primary_chart: NatalTechnicalChart, secondary_chart: NatalTechnicalChart) -> Optional[InterpretationBlock]:
        primary_sun = cls._planet_lookup(primary_chart, "Sun")
        secondary_sun = cls._planet_lookup(secondary_chart, "Sun")
        primary_moon = cls._planet_lookup(primary_chart, "Moon")
        secondary_moon = cls._planet_lookup(secondary_chart, "Moon")
        if not primary_sun or not secondary_sun or not primary_moon or not secondary_moon:
            return None
        summary = (
            f"{primary_sun.sign} solar style meets {secondary_sun.sign} solar style, while the emotional rhythm pairs {primary_moon.sign} with {secondary_moon.sign}. "
            "This gives the relationship an outer style and an inner feeling climate before the more detailed chart links are added."
        )
        return cls._block(
            title=f"How your core styles meet: {primary_sun.sign} and {secondary_sun.sign}",
            summary=summary,
            citations=cls._resolve_labels(["tetrabiblos_sign_expression", "jung_projection_mirror"]),
            block_type="synastry_sign_pair",
        )

    @classmethod
    def _relationship_climate_block(
        cls,
        aspects: List[SynastryAspectRecord],
        bridge_tone: Optional[str] = None,
    ) -> InterpretationBlock:
        supportive = len([aspect for aspect in aspects if aspect.type in {"Trine", "Sextile"}])
        tense = len([aspect for aspect in aspects if aspect.type in {"Square", "Opposition"}])
        unitive = len([aspect for aspect in aspects if aspect.type == "Conjunction"])
        summary = (
            f"This bond currently shows {supportive} supportive contacts, {tense} friction contacts, and {unitive} conjunctions among the strongest visible links. "
            "That mix matters because it shows how much ease, pressure, and focus the relationship may need to carry in real life."
        )
        if bridge_tone == "cooperative":
            summary += " The current year lords are cooperating, so the charts have a better chance of using even difficult patterns productively."
        elif bridge_tone == "demanding":
            summary += " The current year lords are under strain, so the relationship may feel more fated, compressed, or reactive than usual unless both people slow down."
        return cls._block(
            title="The basic feel of this relationship",
            summary=summary,
            citations=cls._resolve_labels(["tetrabiblos_aspect_relation", "traditional_annual_profection"]),
            block_type="relationship_climate",
        )

    @classmethod
    def _levi_current_block(
        cls,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        ontology: Dict,
    ) -> Optional[InterpretationBlock]:
        current = cls._select_levi_current(primary_chart, secondary_chart, aspects, ontology)
        if not current:
            return None
        top_aspect = aspects[0] if aspects else None
        top_phrase = f" One of the strongest links is {top_aspect.first} {top_aspect.type.lower()} {top_aspect.second}." if top_aspect else ""
        summary = (
            f"The strongest symbolic theme in this relationship is {current.get('display_name', 'symbolic correspondence')}. "
            f"{current.get('narrative', '')}{top_phrase}"
        )
        return cls._block(
            title=f"Main symbolic theme in this relationship: {current.get('display_name', 'Correspondence')}",
            summary=summary,
            citations=cls._resolve_labels(["levi_kabbalistic_correspondence", *current.get("source_lens_tags", [])]),
            block_type="levi_current",
        )

    @classmethod
    def _aspect_blocks(cls, aspects: List[SynastryAspectRecord], include_jungian: bool) -> List[InterpretationBlock]:
        blocks: List[InterpretationBlock] = []
        for aspect in aspects[:4]:
            citations = ["tetrabiblos_aspect_relation"]
            if include_jungian and aspect.type == "Square":
                citations.append("jung_tension_of_opposites")
            elif include_jungian and aspect.type in ["Opposition", "Conjunction"]:
                citations.append("jung_projection_mirror")
            summary = (
                f"{aspect.first} forms a {aspect.type.lower()} with {aspect.second} across the two charts. "
                f"This is one of the clearer relationship patterns in the reading, and it is {cls._simple_closeness(aspect)}."
            )
            blocks.append(
                cls._block(
                    title=f"A strong pattern between {aspect.first} and {aspect.second}",
                    summary=summary,
                    citations=cls._resolve_labels(citations),
                    block_type="synastry_aspect",
                )
            )
        return blocks

    @classmethod
    def _venus_mars_block(cls, aspects: List[SynastryAspectRecord]) -> Optional[InterpretationBlock]:
        match = next(
            (
                aspect
                for aspect in aspects
                if {aspect.first, aspect.second} == {"Venus", "Mars"}
            ),
            None,
        )
        if not match:
            return None
        summary = (
            f"Venus and Mars connect by {match.type.lower()}. "
            f"That makes attraction, pace, and pursuit especially visible in the relationship, and this link is {cls._simple_closeness(match)}."
        )
        return cls._block(
            title="How attraction and pursuit show up here",
            summary=summary,
            citations=cls._resolve_labels(["tetrabiblos_aspect_relation", "jung_projection_mirror"]),
            block_type="synastry_attraction",
        )

    @classmethod
    def _sun_moon_block(cls, aspects: List[SynastryAspectRecord]) -> Optional[InterpretationBlock]:
        match = next(
            (
                aspect
                for aspect in aspects
                if {aspect.first, aspect.second} == {"Sun", "Moon"}
            ),
            None,
        )
        if not match:
            return None
        summary = (
            f"A {match.type.lower()} between Sun and Moon appears here. "
            f"That often becomes the basic rhythm between identity, feeling, and care in the relationship, and this link is {cls._simple_closeness(match)}."
        )
        return cls._block(
            title="How identity and feelings move together",
            summary=summary,
            citations=cls._resolve_labels(["tetrabiblos_aspect_relation", "jung_projection_mirror"]),
            block_type="synastry_core_bond",
        )

    @classmethod
    def _red_book_block(cls, primary: BirthProfile, secondary: BirthProfile) -> InterpretationBlock:
        return cls._block(
            title="A reflective prompt for this relationship",
            summary=(
                f"Journal the figures that appear when {primary.name} imagines {secondary.name}, and vice versa. "
                "Treat those inner figures as symbolic presences before treating them as literal truth about the other person."
            ),
            citations=cls._resolve_labels(["red_book_imaginal_prompt"]),
            block_type="synastry_prompt",
        )

    @classmethod
    def build_prediction_cards(
        cls,
        primary: BirthProfile,
        secondary: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        primary_annual_profection: Optional[AnnualProfectionRecord],
        secondary_annual_profection: Optional[AnnualProfectionRecord],
        primary_solar_return: Optional[SolarReturnRecord],
        secondary_solar_return: Optional[SolarReturnRecord],
        topic_judgments: List[TopicJudgmentRecord],
        ontology: Dict,
        include_red_book_prompts: bool,
    ) -> List[PredictionCard]:
        primary_bits = cls._activation_summary_bits(primary, primary_chart, primary_annual_profection, primary_solar_return, ontology)
        secondary_bits = cls._activation_summary_bits(secondary, secondary_chart, secondary_annual_profection, secondary_solar_return, ontology)
        bridge = cls._year_lord_bridge_summary(
            primary,
            secondary,
            primary_chart,
            secondary_chart,
            primary_annual_profection,
            secondary_annual_profection,
            primary_solar_return,
            secondary_solar_return,
            aspects,
            ontology,
        ) if primary_annual_profection and secondary_annual_profection else {"bridge_sentence": "Yearly activation data is incomplete.", "tone": "parallel but separate"}
        primary_year_lord = primary_annual_profection.lord_of_year if primary_annual_profection else None
        secondary_year_lord = secondary_annual_profection.lord_of_year if secondary_annual_profection else None
        prioritized_aspects = sorted(
            aspects,
            key=lambda aspect: cls._contact_priority(aspect, primary_year_lord, secondary_year_lord),
        )
        top_aspect = prioritized_aspects[0] if prioritized_aspects else None
        tense_aspect = next((aspect for aspect in prioritized_aspects if aspect.type in {"Square", "Opposition"}), None)
        sun_moon = next((aspect for aspect in prioritized_aspects if {aspect.first, aspect.second} == {"Sun", "Moon"}), None)
        venus_mars = next((aspect for aspect in prioritized_aspects if {aspect.first, aspect.second} == {"Venus", "Mars"}), None)
        top_topic = topic_judgments[0] if topic_judgments else None
        topic_opportunity, topic_caution, topic_ritual = cls._topic_guidance(top_topic.key) if top_topic else (
            "Read the topic before reading the whole relationship.",
            "Do not flatten one strong topic into a verdict on the bond.",
            "Write down what the relationship is actually asking from each person.",
        )
        tension_phrase = (
            f"{tense_aspect.first} {tense_aspect.type.lower()} {tense_aspect.second}"
            if tense_aspect else
            "projection"
        )

        first_summary = bridge["bridge_sentence"]
        second_summary = (
            f"{primary.name} is currently bringing {primary_bits['activated_topics']} through {primary_bits['year_lord']}, while {secondary.name} is bringing {secondary_bits['activated_topics']} through {secondary_bits['year_lord']}. "
            f"That means the bond is not only about compatibility in the abstract; it is being shaped by two concrete yearly storylines right now."
        )
        third_summary = (
            (
                f"The heaviest repeated testimony right now lands in {top_topic.title.lower()}. "
                + " ".join(item.interpretation for item in top_topic.evidence_items[:2])
            )
            if top_topic else (
                f"The clearest cross-chart contact right now is {top_aspect.first} {top_aspect.type.lower()} {top_aspect.second}, so that is the first pattern to handle consciously."
                if top_aspect else
                "No single cross-chart contact dominates, so the relationship should be read more by each person's yearly activation than by one dramatic pattern."
            )
        )
        if top_aspect:
            third_summary += f" A key carrier of that theme is {top_aspect.first} {top_aspect.type.lower()} {top_aspect.second}."
        if tense_aspect:
            third_summary += (
                f" The sharpest pressure point is {tense_aspect.first} {tense_aspect.type.lower()} {tense_aspect.second}, which should be treated as a work point rather than as proof that the bond is failing."
            )
        elif sun_moon:
            third_summary += (
                f" A key stabilizer is {sun_moon.first} {sun_moon.type.lower()} {sun_moon.second}, which helps identity and feeling stay in contact."
            )

        return [
            PredictionCard(
                key="synastry_yearly_bridge",
                title="How the current years meet",
                timeframe="Current profection year",
                summary=first_summary,
                opportunities=[
                    "Read each person's yearly activation before making a total judgment about the bond.",
                    "Name the year-lord story each person is bringing into the relationship.",
                ],
                cautions=[
                    "Do not flatten two separate yearly activations into one single relationship script.",
                    "A shared strain may come from timing as much as from compatibility.",
                ],
                rituals=[
                    "Have each person name the life area that keeps coming up this year.",
                    "Write down the two year lords before discussing the strongest aspect.",
                ],
                citations=cls._resolve_labels(["traditional_annual_profection", "traditional_solar_return", "tetrabiblos_aspect_relation"]),
            ),
            PredictionCard(
                key="synastry_personal_activation",
                title="What each person is bringing right now",
                timeframe="Current yearly frame",
                summary=second_summary,
                opportunities=[
                    f"Let {primary.name}'s {primary_bits['activated_topics']} storyline be spoken plainly instead of guessed.",
                    f"Let {secondary.name}'s {secondary_bits['activated_topics']} storyline be spoken plainly instead of guessed.",
                ],
                cautions=[
                    "Avoid making one person carry the whole emotional weather system.",
                    "Do not demand the same pace from two very different yearly activations.",
                ],
                rituals=[
                    "Ask each person what house topic keeps repeating this year.",
                    "Compare the two answers before discussing blame or compatibility.",
                ],
                citations=cls._resolve_labels(["traditional_sect_condition", "traditional_annual_profection", "traditional_solar_return"]),
            ),
            PredictionCard(
                key="synastry_topic_focus",
                title="Which relationship topic is carrying the bond",
                timeframe="Current relationship focus",
                summary=third_summary,
                opportunities=[
                    topic_opportunity,
                    f"Use the {venus_mars.first}-{venus_mars.second} chemistry consciously." if venus_mars else "Treat the strongest contact as a conversation topic, not as a verdict.",
                ],
                cautions=[
                    topic_caution,
                    tension_phrase,
                ],
                rituals=(
                    [
                        topic_ritual,
                        "Each person writes one page on what their current year is asking from the relationship."
                    ]
                    if include_red_book_prompts else
                    [topic_ritual]
                ),
                citations=(
                    top_topic.citations
                    if top_topic else
                    cls._resolve_labels(["tetrabiblos_aspect_relation", "traditional_annual_profection"])
                ) + (cls._resolve_labels(["red_book_imaginal_prompt"]) if include_red_book_prompts else []),
            ),
        ]

    @classmethod
    def _build_blocks(
        cls,
        primary: BirthProfile,
        secondary: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        topic_judgments: List[TopicJudgmentRecord],
        primary_annual_profection: Optional[AnnualProfectionRecord],
        secondary_annual_profection: Optional[AnnualProfectionRecord],
        primary_solar_return: Optional[SolarReturnRecord],
        secondary_solar_return: Optional[SolarReturnRecord],
        ontology: Dict,
        include_jungian: bool,
        include_red_book_prompts: bool,
    ) -> List[InterpretationBlock]:
        blocks: List[InterpretationBlock] = []
        primary_frame = cls._current_frame_block(
            primary,
            primary_chart,
            primary_annual_profection,
            primary_solar_return,
            ontology,
            owner_label="Person A",
        )
        if primary_frame:
            blocks.append(primary_frame)
        secondary_frame = cls._current_frame_block(
            secondary,
            secondary_chart,
            secondary_annual_profection,
            secondary_solar_return,
            ontology,
            owner_label="Person B",
        )
        if secondary_frame:
            blocks.append(secondary_frame)

        bridge_tone = None
        if primary_annual_profection and secondary_annual_profection:
            bridge = cls._year_lord_bridge_summary(
                primary,
                secondary,
                primary_chart,
                secondary_chart,
                primary_annual_profection,
                secondary_annual_profection,
                primary_solar_return,
                secondary_solar_return,
                aspects,
                ontology,
            )
            bridge_block = cls._yearly_bridge_block(
                primary,
                secondary,
                primary_chart,
                secondary_chart,
                primary_annual_profection,
                secondary_annual_profection,
                primary_solar_return,
                secondary_solar_return,
                aspects,
                ontology,
            )
            bridge_tone = bridge["tone"]
            if bridge_block:
                blocks.append(bridge_block)

        blocks.extend(cls._build_topic_judgment_blocks(topic_judgments))
        blocks.append(cls._relationship_climate_block(aspects, bridge_tone=bridge_tone))

        prioritized_aspects = sorted(
            aspects,
            key=lambda aspect: cls._contact_priority(
                aspect,
                primary_annual_profection.lord_of_year if primary_annual_profection else None,
                secondary_annual_profection.lord_of_year if secondary_annual_profection else None,
            ),
        )
        sun_moon = cls._sun_moon_block(prioritized_aspects)
        if sun_moon:
            blocks.append(sun_moon)
        venus_mars = cls._venus_mars_block(prioritized_aspects)
        if venus_mars:
            blocks.append(venus_mars)

        generic_aspects = [
            aspect for aspect in prioritized_aspects
            if {aspect.first, aspect.second} not in ({"Sun", "Moon"}, {"Venus", "Mars"})
        ]
        blocks.extend(cls._aspect_blocks(generic_aspects, include_jungian)[:3])

        if include_jungian:
            levi_block = cls._levi_current_block(primary_chart, secondary_chart, aspects, ontology)
            if levi_block:
                levi_block.title = levi_block.title.replace("Main symbolic theme", "Supplemental symbolic theme", 1)
                blocks.append(levi_block)

        if include_red_book_prompts:
            blocks.append(cls._red_book_block(primary, secondary))
        return blocks

    @classmethod
    def _build_planetary_fallback_blocks(
        cls,
        primary: BirthProfile,
        secondary: BirthProfile,
        primary_chart: NatalTechnicalChart,
        secondary_chart: NatalTechnicalChart,
        aspects: List[SynastryAspectRecord],
        include_jungian: bool,
        include_red_book_prompts: bool,
    ) -> List[InterpretationBlock]:
        blocks: List[InterpretationBlock] = []
        sign_block = cls._sign_pair_block(primary_chart, secondary_chart)
        if sign_block:
            sign_block.title = f"Simple mode: {sign_block.title}"
            blocks.append(sign_block)
        if aspects:
            climate = cls._relationship_climate_block(aspects)
            climate.title = "Simple mode relationship climate"
            climate.summary += " Because birth times are not exact, this mode uses only the most stable planet-to-planet patterns and leaves out house and angle claims."
            blocks.append(climate)
        blocks.extend(cls._aspect_blocks(aspects, include_jungian)[:3])
        venus_mars = cls._venus_mars_block(aspects)
        if venus_mars:
            blocks.append(venus_mars)
        sun_moon = cls._sun_moon_block(aspects)
        if sun_moon:
            blocks.append(sun_moon)
        if include_red_book_prompts:
            blocks.append(cls._red_book_block(primary, secondary))
        return blocks

    @classmethod
    def _build_planetary_fallback_prediction_cards(
        cls,
        primary: BirthProfile,
        secondary: BirthProfile,
        aspects: List[SynastryAspectRecord],
        include_red_book_prompts: bool,
    ) -> List[PredictionCard]:
        top_aspect = aspects[0] if aspects else None
        tense_aspect = next((aspect for aspect in aspects if aspect.type in {"Square", "Opposition"}), None)
        bond_aspect = next((aspect for aspect in aspects if {aspect.first, aspect.second} == {"Sun", "Moon"}), None)
        return [
            PredictionCard(
                key="synastry_planetary_fallback_weather",
                title="Simple relationship weather",
                timeframe="Usable now",
                summary=(
                    f"The clearest stable pattern between {primary.name} and {secondary.name} is "
                    f"{top_aspect.first} {top_aspect.type.lower()} {top_aspect.second}."
                    if top_aspect else
                    f"Use the broad planetary tone between {primary.name} and {secondary.name} before claiming anything more detailed."
                ),
                opportunities=["Use the clearest planetary contact as the spine of the reading."],
                cautions=["false certainty", "projecting timed certainty onto a fallback chart"],
                rituals=["Keep the interpretation at the planetary level until both birth times are verified."],
                citations=cls._resolve_labels(["tetrabiblos_aspect_relation"]),
            ),
            PredictionCard(
                key="synastry_planetary_fallback_tension",
                title="Pressure point",
                timeframe="Watch this dynamic",
                summary=(
                    f"The pressure point is {tense_aspect.first} {tense_aspect.type.lower()} {tense_aspect.second}; treat it as something to work through, not a verdict on the relationship."
                    if tense_aspect else
                    "Without a standout hard pattern, the main risk is drift, assumption, or idealization."
                ),
                opportunities=["Name the strongest friction early."],
                cautions=["avoiding clarity"],
                rituals=["Have one exact clarifying conversation."],
                citations=cls._resolve_labels(["tetrabiblos_aspect_relation", "jung_projection_mirror"]),
            ),
            PredictionCard(
                key="synastry_planetary_fallback_upgrade",
                title="How to improve accuracy",
                timeframe="Before relying on house timing",
                summary=(
                    f"{bond_aspect.first} {bond_aspect.type.lower()} {bond_aspect.second} gives a meaningful relationship signature, but the next step is simple: confirm both birth times before trusting house-based timing or finer chart details."
                    if bond_aspect else
                    "The next step is simple: confirm both birth times before trusting house-based timing or finer chart details."
                ),
                opportunities=["Find the birth record that pins down both times."],
                cautions=["mistaking simple mode for a fully timed relationship reading"] ,
                rituals=([
                    "Each person writes what feels stable versus speculative in the bond."
                ] if include_red_book_prompts else ["Rerun the chart once both exact times are confirmed."]),
                citations=cls._resolve_labels(["tetrabiblos_house_topic", *( ["red_book_imaginal_prompt"] if include_red_book_prompts else [] )]),
            ),
        ]

    @classmethod
    def build_response(cls, request: SynastryReadingRequest) -> SynastryReadingResponse:
        ontology = load_ontology()
        counts = {key: len(value) for key, value in ontology.items()}
        source_lenses = cls._build_source_lenses(request)
        notes: List[str] = [
            "Synastry compares two natal structures and then looks for strong cross-chart contacts.",
            "Astrology is treated here as a traditional interpretive discipline, not as a scientifically proven diagnostic system.",
            "The Ark is being re-based on a traditional source-grounded doctrine: natal structure first, optional modern overlays second.",
            "Ontology ingestion is live from structured JSON inside The Ark repository.",
        ]

        primary_profile, primary_resolution, primary_timezone = ProfileResolutionService.resolve_profile(request.primary_profile, notes)
        secondary_profile, secondary_resolution, secondary_timezone = ProfileResolutionService.resolve_profile(request.secondary_profile, notes)

        primary_chart = None
        secondary_chart = None
        transit_chart = None
        primary_transit_aspects = []
        secondary_transit_aspects = []
        transit_timestamp = None
        transit_timezone = None
        transit_location_status = None
        primary_annual_profection = None
        secondary_annual_profection = None
        primary_solar_return = None
        secondary_solar_return = None
        primary_solar_return_chart_data = None
        secondary_solar_return_chart_data = None
        topic_judgments: List[TopicJudgmentRecord] = []
        inter_chart_aspects: List[SynastryAspectRecord] = []
        prediction_cards: List[PredictionCard] = []
        interpretation_blocks: List[InterpretationBlock] = []
        calculation_status = "needs_birth_coordinates"
        engine_status = "waiting_for_geodata"
        status = "contract_ready"
        reading = ReadingSection(
            headline="The Ark synastry instrument is ready.",
            practical_meaning="The API can resolve both birth contexts and compare two charts once sufficient inputs are present.",
            life_translation="The Ark treats synastry as natal structure first, cross-chart contact second, and optional modern overlays after that.",
            guidance="Provide accurate birth context for both people so the relational prediction layer becomes specific.",
            prompt="What is truly happening between the two people, and what belongs to chart structure rather than wish or projection?",
            oracle="The Ark is waiting for enough context to name the bond's live current.",
        )

        can_calculate = all([
            primary_profile.latitude is not None,
            primary_profile.longitude is not None,
            primary_profile.utc_offset,
            secondary_profile.latitude is not None,
            secondary_profile.longitude is not None,
            secondary_profile.utc_offset,
        ])

        if request.primary_profile.time_precision != "exact" or request.secondary_profile.time_precision != "exact":
            if primary_profile.utc_offset and secondary_profile.utc_offset:
                try:
                    primary_chart = NatalChartEngine.calculate_planetary_fallback_chart(
                        birth_date=primary_profile.birth_date,
                        birth_time=primary_profile.birth_time,
                        utc_offset=primary_profile.utc_offset,
                    )
                    secondary_chart = NatalChartEngine.calculate_planetary_fallback_chart(
                        birth_date=secondary_profile.birth_date,
                        birth_time=secondary_profile.birth_time,
                        utc_offset=secondary_profile.utc_offset,
                    )
                    inter_chart_aspects = cls._build_inter_chart_aspects(primary_chart, secondary_chart)
                    interpretation_blocks = cls._build_planetary_fallback_blocks(
                        primary_profile,
                        secondary_profile,
                        primary_chart,
                        secondary_chart,
                        inter_chart_aspects,
                        request.include_jungian,
                        request.include_red_book_prompts,
                    )
                    transit_chart, transit_timestamp, transit_timezone, transit_location_status = TransitForecastService.calculate_current_transit_chart(
                        profile=primary_profile,
                        resolved_timezone=primary_timezone,
                    )
                    primary_transit_aspects = TransitForecastService.build_transit_contacts(
                        profile=primary_profile,
                        transit_chart=transit_chart,
                        natal_chart=primary_chart,
                        natal_owner="primary",
                        transit_timestamp=transit_timestamp,
                    )
                    secondary_transit_aspects = TransitForecastService.build_transit_contacts(
                        profile=primary_profile,
                        transit_chart=transit_chart,
                        natal_chart=secondary_chart,
                        natal_owner="secondary",
                        transit_timestamp=transit_timestamp,
                    )
                    transit_block = TransitForecastService.build_synastry_transit_block(
                        contacts=sorted(primary_transit_aspects + secondary_transit_aspects, key=lambda item: item.orb),
                        transit_timestamp=transit_timestamp,
                        transit_timezone=transit_timezone,
                        ontology=ontology,
                    )
                    if transit_block:
                        interpretation_blocks.append(transit_block)
                    prediction_cards = TransitForecastService.build_synastry_prediction_cards(
                        primary_profile=primary_profile,
                        secondary_profile=secondary_profile,
                        primary_contacts=primary_transit_aspects,
                        secondary_contacts=secondary_transit_aspects,
                        transit_timestamp=transit_timestamp,
                        transit_timezone=transit_timezone,
                        ontology=ontology,
                        include_red_book_prompts=request.include_red_book_prompts,
                    ) or cls._build_planetary_fallback_prediction_cards(
                        primary_profile,
                        secondary_profile,
                        inter_chart_aspects,
                        request.include_red_book_prompts,
                    )
                    status = "synastry_planetary_fallback"
                    calculation_status = "planetary_fallback"
                    engine_status = "planetary_longitudes_ready"
                    reading = ReadingSection(
                        headline=f"Relationship reading in simple mode: {primary_profile.name} and {secondary_profile.name}.",
                        practical_meaning=prediction_cards[0].summary if prediction_cards else "A simpler relationship reading is available.",
                        life_translation="This simpler mode focuses on the most stable planet-to-planet patterns and avoids house or angle claims until both birth times are exact.",
                        guidance=prediction_cards[1].summary if len(prediction_cards) > 1 else "Confirm both birth times before relying on more detailed relationship timing or house-based claims.",
                        prompt="Which birth time is still missing or uncertain?",
                        timing_focus="Simple mode keeps the relationship reading focused on the most reliable shared patterns.",
                        ritual_focus="; ".join(prediction_cards[0].rituals[:2]) if prediction_cards else None,
                        oracle="The Ark is using simple relationship mode until both birth times are exact.",
                    )
                    notes.append("One or both birth times are not exact, so The Ark switched to planetary fallback synastry: planetary contacts remain visible, while house and angle claims are intentionally suppressed.")
                except ChartEngineError as exc:
                    calculation_status = "calculation_error"
                    engine_status = "flatlib_swisseph_error"
                    status = "needs_exact_birth_time"
                    notes.append(f"Planetary fallback synastry could not be calculated: {exc}")
            else:
                calculation_status = "needs_birth_timezone"
                engine_status = "waiting_for_timezone"
                status = "needs_exact_birth_time"
                notes.append("One or both birth times are not exact and a usable UTC offset is still missing, so even planetary fallback synastry could not be calculated yet.")

        elif can_calculate:
            try:
                primary_chart = NatalChartEngine.calculate_natal_chart(
                    birth_date=primary_profile.birth_date,
                    birth_time=primary_profile.birth_time,
                    utc_offset=primary_profile.utc_offset,
                    latitude=primary_profile.latitude,
                    longitude=primary_profile.longitude,
                )
                secondary_chart = NatalChartEngine.calculate_natal_chart(
                    birth_date=secondary_profile.birth_date,
                    birth_time=secondary_profile.birth_time,
                    utc_offset=secondary_profile.utc_offset,
                    latitude=secondary_profile.latitude,
                    longitude=secondary_profile.longitude,
                )
                inter_chart_aspects = cls._build_inter_chart_aspects(primary_chart, secondary_chart)
                transit_chart, transit_timestamp, transit_timezone, transit_location_status = TransitForecastService.calculate_current_transit_chart(
                    profile=primary_profile,
                    resolved_timezone=primary_timezone,
                )
                reference_dt = datetime.fromisoformat(transit_timestamp) if transit_timestamp else None
                primary_annual_profection = TraditionalAstrologyService.build_annual_profection(
                    profile=primary_profile,
                    chart_data=primary_chart,
                    reference_dt=reference_dt,
                )
                secondary_annual_profection = TraditionalAstrologyService.build_annual_profection(
                    profile=secondary_profile,
                    chart_data=secondary_chart,
                    reference_dt=reference_dt,
                )
                primary_solar_return_context = TraditionalAstrologyService.find_current_solar_return_datetime(
                    profile=primary_profile,
                    natal_chart=primary_chart,
                    reference_dt=reference_dt,
                    resolved_timezone=primary_timezone,
                )
                if primary_solar_return_context:
                    sr_year, sr_dt, sr_timezone, sr_latitude, sr_longitude, sr_location_status = primary_solar_return_context
                    primary_solar_return_chart_data = NatalChartEngine.calculate_chart(
                        date_text=sr_dt.strftime("%Y-%m-%d"),
                        time_text=sr_dt.strftime("%H:%M"),
                        utc_offset=TraditionalAstrologyService._format_offset(sr_dt),
                        latitude=sr_latitude,
                        longitude=sr_longitude,
                    )
                    primary_solar_return = TraditionalAstrologyService.build_solar_return_record(
                        solar_year=sr_year,
                        annual_profection=primary_annual_profection,
                        solar_return_chart=primary_solar_return_chart_data,
                        return_dt=sr_dt,
                        timezone_label=sr_timezone,
                        location_status=sr_location_status,
                    )
                secondary_solar_return_context = TraditionalAstrologyService.find_current_solar_return_datetime(
                    profile=secondary_profile,
                    natal_chart=secondary_chart,
                    reference_dt=reference_dt,
                    resolved_timezone=secondary_timezone,
                )
                if secondary_solar_return_context:
                    sr_year, sr_dt, sr_timezone, sr_latitude, sr_longitude, sr_location_status = secondary_solar_return_context
                    secondary_solar_return_chart_data = NatalChartEngine.calculate_chart(
                        date_text=sr_dt.strftime("%Y-%m-%d"),
                        time_text=sr_dt.strftime("%H:%M"),
                        utc_offset=TraditionalAstrologyService._format_offset(sr_dt),
                        latitude=sr_latitude,
                        longitude=sr_longitude,
                    )
                    secondary_solar_return = TraditionalAstrologyService.build_solar_return_record(
                        solar_year=sr_year,
                        annual_profection=secondary_annual_profection,
                        solar_return_chart=secondary_solar_return_chart_data,
                        return_dt=sr_dt,
                        timezone_label=sr_timezone,
                        location_status=sr_location_status,
                    )
                topic_judgments = cls.build_topic_judgments(
                    primary_profile,
                    secondary_profile,
                    primary_chart,
                    secondary_chart,
                    inter_chart_aspects,
                    primary_annual_profection,
                    secondary_annual_profection,
                    primary_solar_return,
                    secondary_solar_return,
                    ontology,
                )
                interpretation_blocks = cls._build_blocks(
                    primary_profile,
                    secondary_profile,
                    primary_chart,
                    secondary_chart,
                    inter_chart_aspects,
                    topic_judgments,
                    primary_annual_profection,
                    secondary_annual_profection,
                    primary_solar_return,
                    secondary_solar_return,
                    ontology,
                    request.include_jungian,
                    request.include_red_book_prompts,
                )
                primary_transit_aspects = TransitForecastService.build_transit_contacts(
                    profile=primary_profile,
                    transit_chart=transit_chart,
                    natal_chart=primary_chart,
                    natal_owner="primary",
                    transit_timestamp=transit_timestamp,
                )
                secondary_transit_aspects = TransitForecastService.build_transit_contacts(
                    profile=primary_profile,
                    transit_chart=transit_chart,
                    natal_chart=secondary_chart,
                    natal_owner="secondary",
                    transit_timestamp=transit_timestamp,
                )
                transit_block = TransitForecastService.build_synastry_transit_block(
                    contacts=sorted(primary_transit_aspects + secondary_transit_aspects, key=lambda item: item.orb),
                    transit_timestamp=transit_timestamp,
                    transit_timezone=transit_timezone,
                    ontology=ontology,
                )
                if transit_block:
                    interpretation_blocks.append(transit_block)
                prediction_cards = cls.build_prediction_cards(
                    primary_profile,
                    secondary_profile,
                    primary_chart,
                    secondary_chart,
                    inter_chart_aspects,
                    primary_annual_profection,
                    secondary_annual_profection,
                    primary_solar_return,
                    secondary_solar_return,
                    topic_judgments,
                    ontology,
                    request.include_red_book_prompts,
                )
                bridge_block = next((block for block in interpretation_blocks if block.block_type == "synastry_yearly_bridge"), None)
                topic_block = next((block for block in interpretation_blocks if block.block_type == "synastry_topic_judgment"), None)
                leading_topic = topic_judgments[0] if topic_judgments else None
                levi_block = next((block for block in interpretation_blocks if block.block_type == "levi_current"), None)
                climate_block = next((block for block in interpretation_blocks if block.block_type == "relationship_climate"), None)
                status = "synastry_calculated"
                calculation_status = "calculated"
                engine_status = "flatlib_swisseph_ready"
                reading = ReadingSection(
                    headline=f"Relationship reading for {primary_profile.name} and {secondary_profile.name}, anchored in two natal frames and two current years.",
                    practical_meaning=(
                        prediction_cards[0].summary
                        if prediction_cards else
                        "This reading compares both birth charts by starting with each person's natal condition and current yearly activation."
                    ),
                    life_translation=(
                        topic_block.summary
                        if topic_block else (
                            climate_block.summary
                            if climate_block else (
                                bridge_block.summary
                                if bridge_block else (
                                    levi_block.summary
                                    if levi_block else
                                    "This relationship reading looks at natal condition, yearly activation, fit, friction, attraction, and misunderstanding instead of reducing everything to simple compatibility."
                                )
                            )
                        )
                    ),
                    guidance=(
                        prediction_cards[1].summary
                        if len(prediction_cards) > 1 else
                        "Name each person's current year first, then ask how the strongest aspect is carrying that pressure or support."
                    ),
                    prompt=(
                        "What does each person's current year ask of the bond before the bond asks anything else of them?"
                        if request.include_red_book_prompts
                        else None
                    ),
                    timing_focus=(
                        "Read the bond through the current profection years first, then use the solar returns to see how differently each person is carrying the same season."
                    ),
                    ritual_focus="; ".join(prediction_cards[0].rituals[:2]) if prediction_cards else None,
                    oracle=(
                        (
                            f"The Ark names {primary_annual_profection.lord_of_year} and {secondary_annual_profection.lord_of_year} as the current carriers of this bond, "
                            f"with {leading_topic.title.lower()} under the strongest repeated testimony."
                        )
                        if primary_annual_profection and secondary_annual_profection and leading_topic else (
                            f"The Ark names {primary_annual_profection.lord_of_year} and {secondary_annual_profection.lord_of_year} as the current carriers of this bond."
                            if primary_annual_profection and secondary_annual_profection else (
                                f"The Ark names this relationship's current emphasis as {prediction_cards[0].title.lower()}."
                                if prediction_cards else (
                                    levi_block.title
                                    if levi_block else
                                    None
                                )
                            )
                        )
                    ),
                )
                notes.append("Both natal charts were calculated successfully and compared for synastry.")
                notes.append("Each natal chart now carries sect, house rulers, Fortune/Spirit, annual profection, and solar return data inside the technical summary.")
                notes.append("Synastry prose now starts from natal condition and yearly activation before reading cross-chart patterns.")
                notes.append("Relationship topic judgments now combine each person's natal topic condition with cross-chart ruler contacts, helper planets, and current-year activation.")
                notes.append("Shared transits are treated as a supplemental current-weather layer after profections and solar returns.")
                if transit_timestamp and transit_timezone:
                    notes.append(f"Transit forecast anchored to {transit_timestamp[:16].replace('T', ' ')} {transit_timezone} using the primary profile's locale.")
                if transit_location_status == "birth_location_fallback":
                    notes.append("Transit houses currently fall back to the primary person's birth location because no separate current location was supplied.")
                elif transit_location_status == "missing_location":
                    notes.append("Transit location data was missing, so house-based transit weather should be treated as low-confidence.")
            except ChartEngineError as exc:
                calculation_status = "calculation_error"
                engine_status = "flatlib_swisseph_error"
                notes.append(f"Chart engine error: {exc}")
        else:
            notes.append("Both birth profiles still need enough place/time context for full synastry calculation and prediction specificity.")

        technical_summary = SynastryTechnicalSummary(
            calculation_status=calculation_status,
            engine_status=engine_status,
            available_ontology_counts=counts,
            house_system=primary_chart.house_system if primary_chart else DEFAULT_HOUSE_SYSTEM_LABEL,
            supported_planets=[planet["display_name"] for planet in ontology["planets"]],
            supported_aspects=[aspect["display_name"] for aspect in ontology["aspects"]],
            primary_input_resolution_status=primary_resolution,
            secondary_input_resolution_status=secondary_resolution,
            primary_resolved_timezone=primary_timezone,
            secondary_resolved_timezone=secondary_timezone,
            precision_mode=("exact" if request.primary_profile.time_precision == "exact" and request.secondary_profile.time_precision == "exact" else "planetary_fallback"),
            primary_chart_data=primary_chart,
            secondary_chart_data=secondary_chart,
            inter_chart_aspects=inter_chart_aspects,
            transit_timestamp=transit_timestamp,
            transit_timezone=transit_timezone,
            transit_location_status=transit_location_status,
            transit_chart_data=transit_chart,
            primary_transit_aspects=primary_transit_aspects,
            secondary_transit_aspects=secondary_transit_aspects,
            primary_annual_profection=primary_annual_profection,
            secondary_annual_profection=secondary_annual_profection,
            primary_solar_return=primary_solar_return,
            secondary_solar_return=secondary_solar_return,
            primary_solar_return_chart_data=primary_solar_return_chart_data,
            secondary_solar_return_chart_data=secondary_solar_return_chart_data,
            topic_judgments=topic_judgments,
        )

        try:
            reading, _, llm_model = ReadingLLMService.synthesize(
                chart_type="synastry",
                reading=reading,
                daily_horoscope=None,
                technical_summary=technical_summary,
                interpretation_blocks=interpretation_blocks,
                source_lenses=source_lenses,
                prediction_cards=prediction_cards,
            )
            if llm_model:
                notes.append(f"Final reading prose synthesized with {llm_model} on top of the chart evidence.")
        except RuntimeError as exc:
            notes.append(str(exc))
            notes.append("The Ark kept the deterministic relationship reading because LLM synthesis was unavailable for this request.")

        return SynastryReadingResponse(
            status=status,
            primary_profile=primary_profile,
            secondary_profile=secondary_profile,
            technical_summary=technical_summary,
            reading=reading,
            source_lenses=source_lenses,
            prediction_cards=prediction_cards,
            interpretation_blocks=interpretation_blocks,
            notes=notes,
        )
