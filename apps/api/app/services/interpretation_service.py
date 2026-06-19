from collections import Counter
from typing import Dict, List, Optional, Tuple

from app.models.chart import (
    AnglePlacement,
    AnnualProfectionRecord,
    AspectRecord,
    EvidenceItem,
    InterpretationBlock,
    NatalTechnicalChart,
    PlanetPlacement,
    PredictionCard,
    ReadingSection,
    SolarReturnRecord,
    TopicJudgmentRecord,
    YearMapRecord,
)
from app.services.citation_service import CitationService


class NatalInterpretationService:
    PLANET_SEQUENCE = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
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
            "key": "body_character",
            "title": "Body, vitality, and character",
            "house_numbers": [1],
            "lot": None,
            "helper_planets": ["Sun", "Moon", "Mercury"],
        },
        {
            "key": "resources",
            "title": "Resources and support",
            "house_numbers": [2, 11],
            "lot": "Fortune",
            "helper_planets": ["Jupiter"],
        },
        {
            "key": "home_parents",
            "title": "Home, parents, and foundations",
            "house_numbers": [4],
            "lot": None,
            "helper_planets": ["Moon", "Saturn"],
        },
        {
            "key": "relationships",
            "title": "Relationships and agreements",
            "house_numbers": [7],
            "lot": None,
            "helper_planets": ["Venus"],
        },
        {
            "key": "action_reputation",
            "title": "Action and reputation",
            "house_numbers": [10],
            "lot": "Spirit",
            "helper_planets": ["Sun", "Jupiter", "Saturn"],
        },
        {
            "key": "creation_children",
            "title": "Creation, pleasure, and children",
            "house_numbers": [5],
            "lot": None,
            "helper_planets": ["Jupiter", "Venus"],
        },
        {
            "key": "illness_affliction",
            "title": "Illness, labor, and hidden pressure",
            "house_numbers": [6, 12],
            "lot": "Fortune",
            "helper_planets": [],
        },
    ]

    @staticmethod
    def _teach_intro(concept: str) -> str:
        return f"In simple terms, {concept}."

    @staticmethod
    def _with_article(value: str) -> str:
        return f"an {value}" if value[:1].lower() in {"a", "e", "i", "o", "u"} else f"a {value}"

    @staticmethod
    def _teaching_summary(meaning: str, why: str, real_life: str, watch_for: str) -> str:
        return (
            f"{meaning[:1].upper() + meaning[1:]}. "
            f"This matters because {why}. "
            f"In daily life, {real_life}. "
            f"One thing to watch for is {watch_for}."
        )

    @staticmethod
    def _planet_lookup(ontology: Dict) -> Dict[str, Dict]:
        return {item["display_name"]: item for item in ontology["planets"]}

    @staticmethod
    def _sign_lookup(ontology: Dict) -> Dict[str, Dict]:
        return {item["display_name"]: item for item in ontology["signs"]}

    @staticmethod
    def _house_lookup(ontology: Dict) -> Dict[int, Dict]:
        return {item["house_number"]: item for item in ontology["houses"]}

    @staticmethod
    def _aspect_lookup(ontology: Dict) -> Dict[str, Dict]:
        return {item["display_name"]: item for item in ontology["aspects"]}

    @staticmethod
    def _levi_lookup(ontology: Dict) -> List[Dict]:
        return ontology.get("levi_currents", [])

    @staticmethod
    def _find_planet(chart_data: NatalTechnicalChart, name: str) -> Optional[PlanetPlacement]:
        return next((planet for planet in chart_data.planets if planet.id == name), None)

    @staticmethod
    def _find_angle(chart_data: NatalTechnicalChart, name: str) -> Optional[AnglePlacement]:
        return next((angle for angle in chart_data.angles if angle.id == name), None)

    @staticmethod
    def _find_aspect(chart_data: NatalTechnicalChart, first: str, second: str, aspect_type: str) -> Optional[AspectRecord]:
        for aspect in chart_data.aspects:
            matches_pair = {aspect.first, aspect.second} == {first, second}
            if matches_pair and aspect.type == aspect_type:
                return aspect
        return None

    @staticmethod
    def _house_number(house_id: str) -> int:
        return int(house_id.replace("House", ""))

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

    @staticmethod
    def _style_phrase(sign_meta: Dict) -> str:
        return ", ".join(sign_meta.get("classical_style", [])[:3])

    @staticmethod
    def _resolve_labels(citation_ids: List[str]) -> List[str]:
        resolved = CitationService.resolve(citation_ids)
        return [item.get("label", item.get("id", "")) for item in resolved]

    @staticmethod
    def _title_from_house(house_meta: Dict, fallback: str) -> str:
        return house_meta.get("display_name", fallback)

    @staticmethod
    def _house_id_from_number(house_number: int) -> str:
        return f"House{house_number}"

    @classmethod
    def _house_meta(cls, ontology: Dict, house_number: int) -> Dict:
        return cls._house_lookup(ontology).get(house_number, {})

    @classmethod
    def _house_title_for_id(cls, ontology: Dict, house_id: Optional[str]) -> str:
        if not house_id:
            return "an unknown place"
        return cls._title_from_house(cls._house_meta(ontology, cls._house_number(house_id)), house_id)

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
    def _is_aversion(cls, start_sign: str, end_sign: str) -> bool:
        return cls._sign_relation(start_sign, end_sign) is None

    @classmethod
    def _is_superior_witness(cls, witness_sign: str, target_sign: str) -> bool:
        return cls._sign_distance(witness_sign, target_sign) in {2, 3, 4}

    @staticmethod
    def _lot_from_name(chart_data: NatalTechnicalChart, lot_name: str):
        if not chart_data.traditional_context:
            return None
        if lot_name == "Fortune":
            return chart_data.traditional_context.fortune
        if lot_name == "Spirit":
            return chart_data.traditional_context.spirit
        return None

    @classmethod
    def _planet_condition_phrase(cls, planet: Optional[PlanetPlacement]) -> str:
        if not planet:
            return "condition unavailable"
        phrases: List[str] = []
        if planet.traditional_strength:
            phrases.append(planet.traditional_strength)
        if planet.house_condition:
            phrases.append(planet.house_condition)
        if planet.sect_status == "in_sect":
            phrases.append("in sect")
        elif planet.sect_status == "contrary_to_sect":
            phrases.append("contrary to sect")
        if "domicile" in planet.essential_dignities:
            phrases.append("in domicile")
        elif "exaltation" in planet.essential_dignities:
            phrases.append("in exaltation")
        elif "triplicity" in planet.essential_dignities:
            phrases.append("holding triplicity dignity")
        if planet.essential_debilities:
            phrases.append("carrying " + "/".join(planet.essential_debilities))
        if planet.visibility_status in {"combust", "under_beams", "cazimi"}:
            phrases.append(planet.visibility_status.replace("_", " "))
        return ", ".join(phrases[:4]) if phrases else "mixed"

    @classmethod
    def _topic_house_sentence(cls, ontology: Dict, house_number: int) -> str:
        house_meta = cls._house_meta(ontology, house_number)
        topics = cls._topic_phrase(house_meta.get("classical_topics", []) or house_meta.get("modern_topics", []), 3)
        return f"{cls._title_from_house(house_meta, cls._house_id_from_number(house_number))} covers {topics}"

    @classmethod
    def _topic_score_bucket(cls, score: int, activation_score: int, support_score: int, strain_score: int) -> str:
        if support_score >= strain_score + 2:
            return "supportive"
        if strain_score >= support_score + 2 and strain_score >= 3:
            return "difficult"
        if activation_score >= 3 and support_score + strain_score <= 3:
            return "emphasized"
        return "mixed"

    @staticmethod
    def _confidence_label(evidence_count: int, activation_score: int, support_score: int, strain_score: int) -> str:
        contradiction = support_score > 0 and strain_score > 0
        if evidence_count >= 4 and max(activation_score, support_score, strain_score) >= 3 and not contradiction:
            return "high"
        if evidence_count >= 2:
            return "medium"
        return "low"

    @staticmethod
    def _confidence_effect_from_score(score: int) -> str:
        if score > 0:
            return "supports"
        if score < 0:
            return "pressures"
        return "qualifies"

    @staticmethod
    def _confidence_explainer(label: Optional[str], classification: Optional[str] = None) -> Optional[str]:
        if label == "high":
            return "High confidence means several traditional factors point in the same direction."
        if label == "medium":
            if classification == "mixed":
                return "Medium confidence here means the chart shows both support and friction, and several factors repeat that mixed picture."
            if classification == "emphasized":
                return "Medium confidence here means the topic is clearly activated, but activation is not the same thing as pure help or pure strain."
            return "Medium confidence means several factors point this way, but the testimony is not unanimous."
        if label == "low":
            return "Low confidence means the chart offers a clue, but the testimony is still thin or divided."
        return None

    @staticmethod
    def _planet_topic_role(planet_name: str) -> str:
        return {
            "Sun": "identity, visibility, purpose, and public vitality",
            "Moon": "habit, mood, embodiment, and daily responsiveness",
            "Mercury": "thinking, speech, decisions, and interpretation",
            "Venus": "attraction, ease, exchange, value, and relationship",
            "Mars": "action, defense, pressure, urgency, and conflict",
            "Jupiter": "growth, coherence, protection, belief, and increase",
            "Saturn": "limits, duty, endurance, realism, and long-term consequence",
        }.get(planet_name, "how this topic acts, responds, and carries its story")

    @classmethod
    def _evidence_item(
        cls,
        observation: str,
        rule: str,
        interpretation: str,
        score: int,
        caveat: Optional[str] = None,
        source_layer: str = "traditional_core",
        polarity: Optional[str] = None,
        chart_context: Optional[str] = None,
    ) -> EvidenceItem:
        combined = f"{observation} {rule}".lower()
        resolved_source_layer = source_layer
        if source_layer == "traditional_core":
            if any(token in combined for token in ["annual profection", "solar return", "year lord", "profection year"]):
                resolved_source_layer = "traditional_timing"
            elif any(token in combined for token in ["transit", "current sky", "moving sky"]):
                resolved_source_layer = "current_sky"
        resolved_chart_context = chart_context
        if resolved_chart_context is None:
            if "solar return" in combined:
                resolved_chart_context = "solar_return"
            elif "annual profection" in combined or "profection year" in combined or "year lord" in combined:
                resolved_chart_context = "annual_profection"
            elif "fortune" in combined or "spirit" in combined:
                resolved_chart_context = "fortune_spirit"
            elif "transit" in combined or "current sky" in combined or "moving sky" in combined:
                resolved_chart_context = "transit"
            else:
                resolved_chart_context = "natal"
        resolved_polarity = polarity
        if resolved_polarity is None:
            if score > 0:
                resolved_polarity = "support"
            elif score < 0:
                resolved_polarity = "strain"
            else:
                resolved_polarity = "activation"
        return EvidenceItem(
            observation=observation,
            rule=rule,
            source_layer=resolved_source_layer,
            interpretation=interpretation,
            confidence_effect=cls._confidence_effect_from_score(score),
            caveat=caveat,
            polarity=resolved_polarity,
            weight=max(abs(score), 1),
            chart_context=resolved_chart_context,
        )

    @classmethod
    def _helper_planet_score(cls, planet: Optional[PlanetPlacement]) -> int:
        if not planet:
            return 0
        if planet.traditional_strength == "strong":
            return 1
        if planet.traditional_strength == "weak":
            return -1
        return 0

    @classmethod
    def _house_sign(cls, chart_data: NatalTechnicalChart, house_number: int) -> Optional[str]:
        if 1 <= house_number <= len(chart_data.houses):
            return chart_data.houses[house_number - 1].sign
        return None

    @classmethod
    def _witness_score(cls, planet: PlanetPlacement, relation: str) -> int:
        if planet.id in cls.BENEFICS:
            score = 1
            if relation in {"Trine", "Sextile"}:
                score += 1
            if planet.traditional_strength == "strong":
                score += 1
            return score
        if planet.id in cls.MALEFICS:
            score = 1
            if planet.sect_status == "contrary_to_sect":
                score += 1
            if relation in {"Square", "Opposition"}:
                score += 1
            return -score
        if planet.traditional_strength == "strong" and relation in {"Trine", "Sextile", "Conjunction"}:
            return 1
        if planet.traditional_strength == "weak" and relation in {"Square", "Opposition"}:
            return -1
        return 0

    @classmethod
    def _condition_modifier(cls, planet: PlanetPlacement) -> Tuple[int, List[EvidenceItem]]:
        score = 0
        evidence: List[EvidenceItem] = []
        if planet.visibility_status == "cazimi":
            score += 2
            evidence.append(
                cls._evidence_item(
                    observation=f"{planet.id} is cazimi.",
                    rule="A planet at the heart of the Sun is treated as exceptionally concentrated rather than hidden.",
                    interpretation=f"{planet.id} can act with unusual focus despite solar contact.",
                    score=2,
                )
            )
        elif planet.visibility_status in {"combust", "under_beams"}:
            penalty = -2 if planet.visibility_status == "combust" else -1
            score += penalty
            evidence.append(
                cls._evidence_item(
                    observation=f"{planet.id} is {planet.visibility_status.replace('_', ' ')}.",
                    rule="Invisible or combust planets are less able to act openly in traditional judgment.",
                    interpretation=f"{planet.id} is less reliable as a straightforward significator here.",
                    score=penalty,
                    caveat="Combustion can describe pressure, obscurity, or over-identification rather than total failure.",
                )
            )
        if planet.movement_status in {"stationing", "retrograde"}:
            modifier = -1 if planet.movement_status == "retrograde" else 0
            score += modifier
            evidence.append(
                cls._evidence_item(
                    observation=f"{planet.id} is {planet.movement_status}.",
                    rule="Retrograde or stationing motion qualifies how directly a planet can carry out its topics.",
                    interpretation=f"{planet.id} may act in a delayed, recursive, or unstable way.",
                    score=modifier,
                    caveat="Retrograde planets can still be effective, but they tend to work less directly.",
                )
            )
        return score, evidence

    @classmethod
    def _aspect_support_score(cls, planet: PlanetPlacement, aspect_type: str) -> int:
        if planet.id in cls.BENEFICS:
            return 2 if aspect_type in {"Trine", "Sextile", "Conjunction"} and planet.traditional_strength == "strong" else 1
        if planet.id in cls.MALEFICS:
            score = 1
            if planet.sect_status == "contrary_to_sect":
                score += 1
            if aspect_type in {"Square", "Opposition"}:
                score += 1
            return -score
        if planet.traditional_strength == "strong" and aspect_type in {"Trine", "Sextile", "Conjunction"}:
            return 1
        if planet.traditional_strength == "weak" and aspect_type in {"Square", "Opposition"}:
            return -1
        return 0

    @classmethod
    def _planetary_witnesses_house(cls, chart_data: NatalTechnicalChart, house_number: int) -> List[Tuple[PlanetPlacement, str, bool]]:
        house_sign = cls._house_sign(chart_data, house_number)
        if not house_sign:
            return []
        witnesses: List[Tuple[PlanetPlacement, str, bool]] = []
        for planet in chart_data.planets:
            relation = cls._sign_relation(planet.sign, house_sign)
            if relation:
                witnesses.append((planet, relation, cls._is_superior_witness(planet.sign, house_sign)))
        return witnesses

    @classmethod
    def _topic_judgment_data(cls, chart_data: NatalTechnicalChart, ontology: Dict, config: Dict) -> TopicJudgmentRecord:
        houses = cls._house_lookup(ontology)
        score = 0
        activation_score = 0
        support_score = 0
        strain_score = 0
        evidence_items: List[EvidenceItem] = []
        topic_citations = {
            "tetrabiblos_house_topic",
            "tetrabiblos_planetary_quality",
            "traditional_sect_condition",
        }
        benefic_support = 0
        malefic_pressure = 0
        benefic_rescue_present = False
        weak_or_hidden_ruler = False

        for house_number in config["house_numbers"]:
            house_meta = houses.get(house_number, {})
            house_title = cls._title_from_house(house_meta, cls._house_id_from_number(house_number))
            house_sign = cls._house_sign(chart_data, house_number)
            ruler_record = next(
                (
                    record for record in (chart_data.traditional_context.house_rulers if chart_data.traditional_context else [])
                    if record.house_number == house_number
                ),
                None,
            )
            ruler = cls._find_planet(chart_data, ruler_record.ruler) if ruler_record else None
            occupants = [planet for planet in chart_data.planets if planet.house == cls._house_id_from_number(house_number)]

            if ruler:
                activation_score += 1
                if ruler.traditional_strength == "strong":
                    ruler_score = 2
                elif ruler.traditional_strength == "weak":
                    ruler_score = -2
                    weak_or_hidden_ruler = True
                else:
                    ruler_score = 1
                score += ruler_score
                if ruler_score > 0:
                    support_score += ruler_score
                elif ruler_score < 0:
                    strain_score += abs(ruler_score)
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"{house_title} is ruled by {ruler.id}, placed in {ruler.sign} {cls._house_title_for_id(ontology, ruler.house)} with {cls._planet_condition_phrase(ruler)} condition."
                        ),
                        rule="Traditional topic judgment starts with the house ruler before isolated placements.",
                        interpretation=(
                            f"{ruler.id} rules this topic, so it describes {cls._planet_topic_role(ruler.id)}."
                        ),
                        score=ruler_score,
                        caveat="A dignified ruler still needs witness and activation to produce consistent outcomes." if ruler_score > 0 else None,
                    )
                )
                condition_score, condition_evidence = cls._condition_modifier(ruler)
                score += condition_score
                if condition_score > 0:
                    support_score += condition_score
                elif condition_score < 0:
                    strain_score += abs(condition_score)
                if condition_evidence:
                    topic_citations.add("traditional_visibility_motion")
                    weak_or_hidden_ruler = weak_or_hidden_ruler or condition_score < 0
                    evidence_items.extend(condition_evidence)
                if house_sign and cls._is_aversion(ruler.sign, house_sign):
                    score -= 2
                    strain_score += 2
                    weak_or_hidden_ruler = True
                    evidence_items.append(
                        cls._evidence_item(
                            observation=f"{ruler.id} is in aversion to {house_title}.",
                            rule="A ruler that cannot see its own house cannot witness or coordinate that topic directly.",
                            interpretation=f"{house_title} is harder to manage cleanly because its ruler is turned away from it.",
                            score=-2,
                            caveat="A topic in aversion can still improve when other strong witnesses step in.",
                        )
                    )
                    topic_citations.add("traditional_aversion_witness")
                elif house_sign:
                    relation = cls._sign_relation(ruler.sign, house_sign)
                    relation_score = 0
                    if relation in {"Conjunction", "Trine", "Sextile"}:
                        relation_score += 1
                    if cls._is_superior_witness(ruler.sign, house_sign):
                        relation_score += 1
                        topic_citations.add("traditional_overcoming")
                    else:
                        topic_citations.add("traditional_aversion_witness")
                    if relation_score:
                        score += relation_score
                        support_score += relation_score
                        evidence_items.append(
                            cls._evidence_item(
                                observation=(
                                    f"{ruler.id} sees {house_title} by {relation.lower() if relation else 'aspect'}"
                                    + (" from the superior side." if cls._is_superior_witness(ruler.sign, house_sign) else ".")
                                ),
                                rule="A ruler that can witness its house, especially from the superior side, is more able to direct the topic.",
                                interpretation=f"{house_title} is easier to steer because its ruler can testify directly to it.",
                                score=relation_score,
                            )
                        )

            for occupant in occupants[:3]:
                activation_score += 1
                if occupant.id in cls.BENEFICS:
                    occupant_score = 1 if occupant.traditional_strength != "weak" else 0
                    if occupant_score > 0:
                        benefic_support += 1
                elif occupant.id in cls.MALEFICS:
                    occupant_score = -2 if occupant.sect_status == "contrary_to_sect" else -1
                    malefic_pressure += 1
                elif occupant.traditional_strength == "strong":
                    occupant_score = 1
                elif occupant.traditional_strength == "weak":
                    occupant_score = -1
                else:
                    occupant_score = 0
                score += occupant_score
                if occupant_score > 0:
                    support_score += occupant_score
                elif occupant_score < 0:
                    strain_score += abs(occupant_score)
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"{occupant.id} occupies {house_title} with {cls._planet_condition_phrase(occupant)} condition.",
                        rule="Planets placed in a house add direct testimony to that topic.",
                        interpretation=f"{occupant.id} makes this topic more immediately visible in lived experience.",
                        score=occupant_score,
                        caveat="Occupancy intensifies a topic, but it does not replace the house ruler's role.",
                    )
                )

            witnesses = [
                (planet, relation, superior)
                for planet, relation, superior in cls._planetary_witnesses_house(chart_data, house_number)
                if not ruler or planet.id != ruler.id
            ]
            benefic_witnesses = [
                (planet, relation, superior)
                for planet, relation, superior in witnesses
                if planet.id in cls.BENEFICS
            ]
            malefic_witnesses = [
                (planet, relation, superior)
                for planet, relation, superior in witnesses
                if planet.id in cls.MALEFICS
            ]

            if benefic_witnesses:
                best_benefic = max(
                    benefic_witnesses,
                    key=lambda item: cls._witness_score(item[0], item[1]) + (1 if item[2] else 0),
                )
                benefic_score = cls._witness_score(best_benefic[0], best_benefic[1]) + (1 if best_benefic[2] else 0)
                score += benefic_score
                if benefic_score > 0:
                    support_score += benefic_score
                benefic_support += 1
                benefic_rescue_present = True
                topic_citations.add("traditional_overcoming" if best_benefic[2] else "traditional_aversion_witness")
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"{best_benefic[0].id} witnesses {house_title} by {best_benefic[1].lower()}"
                            + (" from the superior side." if best_benefic[2] else ".")
                        ),
                        rule="Benefic witnesses can steady a topic when they actually see it.",
                        interpretation=f"{house_title} receives constructive support rather than standing alone.",
                        score=benefic_score,
                    )
                )
            elif ruler and weak_or_hidden_ruler:
                score -= 1
                strain_score += 1
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"No benefic witness directly steadies {house_title}.",
                        rule="A weak or averted ruler is harder to rescue when benefics cannot testify to the house.",
                        interpretation=f"{house_title} depends more on strain-management than on easy support.",
                        score=-1,
                        caveat="Absence of benefic witness is a qualifier, not a permanent sentence.",
                    )
                )
                topic_citations.add("traditional_aversion_witness")

            if malefic_witnesses:
                strongest_malefic = min(
                    malefic_witnesses,
                    key=lambda item: cls._witness_score(item[0], item[1]) - (1 if item[2] else 0),
                )
                malefic_score = cls._witness_score(strongest_malefic[0], strongest_malefic[1]) - (1 if strongest_malefic[2] else 0)
                score += malefic_score
                if malefic_score < 0:
                    strain_score += abs(malefic_score)
                malefic_pressure += 1
                topic_citations.add("traditional_overcoming" if strongest_malefic[2] else "traditional_aversion_witness")
                evidence_items.append(
                    cls._evidence_item(
                        observation=(
                            f"{strongest_malefic[0].id} presses {house_title} by {strongest_malefic[1].lower()}"
                            + (" from the superior side." if strongest_malefic[2] else ".")
                        ),
                        rule="Malefic pressure is harder when a malefic can witness, especially from the superior side or out of sect.",
                        interpretation=f"{house_title} carries more friction, delay, or cost than a simpler reading would suggest.",
                        score=malefic_score,
                        caveat="Pressure can describe necessary labor or realism, not only damage.",
                    )
                )
                topic_citations.add("traditional_maltreatment_bonification")

            if ruler:
                ruler_aspects = [
                    aspect for aspect in chart_data.aspects
                    if ruler.id in {aspect.first, aspect.second}
                ]
                for aspect in ruler_aspects[:3]:
                    other_name = aspect.second if aspect.first == ruler.id else aspect.first
                    other_planet = cls._find_planet(chart_data, other_name)
                    if not other_planet:
                        continue
                    aspect_score = cls._aspect_support_score(other_planet, aspect.type)
                    if aspect_score == 0:
                        continue
                    score += aspect_score
                    if aspect_score > 0:
                        support_score += aspect_score
                    elif aspect_score < 0:
                        strain_score += abs(aspect_score)
                    descriptor = "supports" if aspect_score > 0 else "presses"
                    superior = cls._is_superior_witness(other_planet.sign, ruler.sign)
                    if other_planet.id in cls.BENEFICS and aspect_score > 0:
                        benefic_support += 1
                        benefic_rescue_present = True
                    if other_planet.id in cls.MALEFICS and aspect_score < 0:
                        malefic_pressure += 1
                    topic_citations.add("tetrabiblos_aspect_relation")
                    if superior:
                        topic_citations.add("traditional_overcoming")
                    evidence_items.append(
                        cls._evidence_item(
                            observation=(
                                f"{other_planet.id} {descriptor} the ruler by {aspect.type.lower()}"
                                + (" from the superior side." if superior else ".")
                            ),
                            rule="Aspects to the ruler change how much support or pressure the topic can sustain.",
                            interpretation=f"{other_planet.id} modifies the ruler's ability to carry {house_title}.",
                            score=aspect_score,
                        )
                    )

        if config["key"] == "body_character" and chart_data.traditional_context and chart_data.traditional_context.sect_light:
            sect_light = cls._find_planet(chart_data, chart_data.traditional_context.sect_light)
            if sect_light:
                sect_light_score = 1 if sect_light.traditional_strength == "strong" else (-1 if sect_light.traditional_strength == "weak" else 0)
                score += sect_light_score
                activation_score += 1
                if sect_light_score > 0:
                    support_score += sect_light_score
                elif sect_light_score < 0:
                    strain_score += abs(sect_light_score)
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"The sect light is {sect_light.id}, placed in {sect_light.sign} {cls._house_title_for_id(ontology, sect_light.house)}.",
                        rule="Body and character are read through the Ascendant together with the sect light and luminaries.",
                        interpretation=f"{sect_light.id} adds vitality and orientation to how the first-house story becomes visible.",
                        score=sect_light_score,
                    )
                )

        lot = cls._lot_from_name(chart_data, config["lot"]) if config.get("lot") else None
        if lot:
            lot_house_number = cls._house_number(lot.house) if lot.house else None
            lot_ruler = cls._find_planet(chart_data, lot.ruler)
            lot_score = 0
            if lot_ruler:
                activation_score += 1
                if lot_ruler.traditional_strength == "strong":
                    lot_score += 2
                elif lot_ruler.traditional_strength == "weak":
                    lot_score -= 1
            if lot_house_number in config["house_numbers"]:
                lot_score += 1
                activation_score += 1
            score += lot_score
            if lot_score > 0:
                support_score += lot_score
            elif lot_score < 0:
                strain_score += abs(lot_score)
            evidence_items.append(
                cls._evidence_item(
                    observation=(
                        f"{lot.name} falls in {lot.sign} {cls._house_title_for_id(ontology, lot.house)} and is ruled by {lot.ruler}, which is {cls._planet_condition_phrase(lot_ruler)}."
                    ),
                    rule="Relevant lots refine topical judgment by showing where bodily circumstance or intentional direction concentrates.",
                    interpretation=f"{lot.name} adds another layer of testimony to {config['title'].lower()}.",
                    score=lot_score,
                )
            )
            topic_citations.add("traditional_fortune_spirit")

        for helper_name in config.get("helper_planets", []):
            helper = cls._find_planet(chart_data, helper_name)
            helper_score = cls._helper_planet_score(helper)
            score += helper_score
            if helper:
                activation_score += 1
            if helper_score > 0:
                support_score += helper_score
            elif helper_score < 0:
                strain_score += abs(helper_score)
            if helper:
                evidence_items.append(
                    cls._evidence_item(
                        observation=f"{helper.id} is {cls._planet_condition_phrase(helper)}.",
                        rule="Relevant helper planets modify how gracefully a topic can be supported in practice.",
                        interpretation=f"{helper.id} changes the available style of help for this topic.",
                        score=helper_score,
                    )
                )

        if benefic_support >= 2 and weak_or_hidden_ruler:
            score += 1
            support_score += 1
            evidence_items.append(
                cls._evidence_item(
                    observation="Multiple benefic testimonies repeat around a strained significator.",
                    rule="Bonification occurs when benefic support steadies a topic that would otherwise be weaker or harsher.",
                    interpretation="The topic is not effortless, but it is more salvageable than the stress alone suggests.",
                    score=1,
                )
            )
            topic_citations.add("traditional_maltreatment_bonification")
        if malefic_pressure >= 2 and (weak_or_hidden_ruler or not benefic_rescue_present):
            score -= 2
            strain_score += 2
            evidence_items.append(
                cls._evidence_item(
                    observation="Repeated malefic pressure lands on a topic that lacks easy rescue.",
                    rule="Maltreatment grows when malefic testimony repeats around a weak, hidden, or unsupported significator.",
                    interpretation="This topic needs planning, boundaries, and pacing rather than optimistic simplification.",
                    score=-2,
                    caveat="Difficult testimony should be communicated as strain or vulnerability, not fatal certainty.",
                )
            )
            topic_citations.add("traditional_maltreatment_bonification")

        classification = cls._topic_score_bucket(score, activation_score, support_score, strain_score)
        if classification == "difficult" and support_score >= strain_score:
            classification = "mixed"
        confidence = cls._confidence_label(len(evidence_items), activation_score, support_score, strain_score)
        return TopicJudgmentRecord(
            key=config["key"],
            title=config["title"],
            score=score,
            classification=classification,
            confidence=confidence,
            activation_score=activation_score,
            support_score=support_score,
            strain_score=strain_score,
            relevant_houses=list(config["house_numbers"]),
            relevant_lot=config.get("lot"),
            evidence_items=evidence_items,
            citations=cls._resolve_labels(sorted(topic_citations)),
        )

    @classmethod
    def build_topic_judgments(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> List[TopicJudgmentRecord]:
        return [cls._topic_judgment_data(chart_data, ontology, config) for config in cls.TOPIC_CONFIGS]

    @classmethod
    def _fortune_spirit_alignment(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        context = chart_data.traditional_context
        if not context or not context.fortune or not context.spirit:
            return None, None, None
        fortune_house_title = cls._house_title_for_id(ontology, context.fortune.house)
        spirit_house_title = cls._house_title_for_id(ontology, context.spirit.house)
        fortune_house_meta = cls._house_meta(ontology, cls._house_number(context.fortune.house)) if context.fortune.house else {}
        spirit_house_meta = cls._house_meta(ontology, cls._house_number(context.spirit.house)) if context.spirit.house else {}
        fortune_text = (
            f"Fortune in {fortune_house_title} points circumstances toward "
            f"{cls._topic_phrase(fortune_house_meta.get('classical_topics', []) or fortune_house_meta.get('modern_topics', []), 3)}."
        )
        spirit_text = (
            f"Spirit in {spirit_house_title} points chosen effort toward "
            f"{cls._topic_phrase(spirit_house_meta.get('classical_topics', []) or spirit_house_meta.get('modern_topics', []), 3)}."
        )
        if context.fortune.house == context.spirit.house or context.fortune.ruler == context.spirit.ruler:
            return "aligned", fortune_text, spirit_text
        return "split", fortune_text, spirit_text

    @classmethod
    def build_year_map_record(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        annual_profection: Optional[AnnualProfectionRecord],
        solar_return: Optional[SolarReturnRecord],
    ) -> Optional[YearMapRecord]:
        if not annual_profection and not solar_return:
            return None
        alignment, fortune_text, spirit_text = cls._fortune_spirit_alignment(chart_data, ontology)
        activated_house_title = None
        activated_topics: List[str] = []
        profection_window = None
        lord_of_year_condition = None
        if annual_profection:
            house_meta = cls._house_meta(ontology, annual_profection.activated_house)
            activated_house_title = cls._title_from_house(house_meta, cls._house_id_from_number(annual_profection.activated_house))
            activated_topics = (
                [
                    "shared resources, obligations, and vulnerability",
                    "debts, taxes, inheritances, trust, and dependency",
                    "loss, mortality symbolism, and the fears that come with uncertainty",
                ]
                if annual_profection.activated_house == 8 else
                (house_meta.get("classical_topics", []) or house_meta.get("modern_topics", []))[:3]
            )
            if annual_profection.starts_at and annual_profection.ends_at:
                profection_window = f"{annual_profection.starts_at[:10]} to {annual_profection.ends_at[:10]}"
            lord_of_year = cls._find_planet(chart_data, annual_profection.lord_of_year)
            lord_of_year_condition = cls._planet_condition_phrase(lord_of_year)
        guidance_parts: List[str] = []
        if activated_house_title and annual_profection:
            guidance_parts.append(
                f"Start with {activated_house_title.lower()} matters because that is the live profection house."
            )
        if solar_return and solar_return.year_lord_house:
            guidance_parts.append(
                f"Watch {cls._house_title_for_id(ontology, solar_return.year_lord_house).lower()} for where the year lord becomes concrete."
            )
        if alignment == "split":
            guidance_parts.append(
                "Do not confuse what is easiest circumstantially with what is most intentional or purposive this year."
            )
        elif alignment == "aligned":
            guidance_parts.append(
                "Circumstance and intention are pointing in a similar direction, so repeated themes should be taken seriously."
            )
        return YearMapRecord(
            activated_house=annual_profection.activated_house if annual_profection else None,
            activated_house_title=activated_house_title,
            activated_topics=activated_topics,
            profection_window=profection_window,
            lord_of_year=annual_profection.lord_of_year if annual_profection else None,
            lord_of_year_condition=lord_of_year_condition,
            lord_of_year_house=annual_profection.lord_of_year_house if annual_profection else None,
            solar_return_ascendant=solar_return.return_ascendant_sign if solar_return else None,
            solar_return_sun_house=solar_return.sun_house if solar_return else None,
            solar_return_year_lord_house=solar_return.year_lord_house if solar_return else None,
            solar_return_angular_planets=solar_return.angular_planets if solar_return else [],
            fortune_emphasis=fortune_text,
            spirit_emphasis=spirit_text,
            fortune_spirit_alignment=alignment,
            guidance=" ".join(guidance_parts) if guidance_parts else None,
        )

    @classmethod
    def _build_year_map_block(
        cls,
        year_map: Optional[YearMapRecord],
        ontology: Dict,
    ) -> Optional[InterpretationBlock]:
        if not year_map:
            return None
        activated_topics = cls._topic_phrase(year_map.activated_topics, 3)
        summary_bits = []
        if year_map.activated_house_title:
            summary_bits.append(
                f"This year centers {year_map.activated_house_title}, so the main storyline keeps returning to {activated_topics}."
            )
        if year_map.lord_of_year:
            summary_bits.append(
                f"Natal {year_map.lord_of_year} carries the year from the natal {cls._house_title_for_id(ontology, year_map.lord_of_year_house).lower()}, which shows where the yearly theme is most likely to become concrete."
            )
        if year_map.solar_return_ascendant:
            summary_bits.append(
                f"The solar return rises in {year_map.solar_return_ascendant}, and the return Sun falls in the solar-return {cls._house_title_for_id(ontology, year_map.solar_return_sun_house).lower()}."
            )
        if year_map.fortune_spirit_alignment == "aligned":
            summary_bits.append("Fortune and Spirit are aligned, so circumstance and intention are pointing in a similar direction.")
        elif year_map.fortune_spirit_alignment == "split":
            summary_bits.append("Fortune and Spirit are split across a real axis, so what life is demanding and what you most want to pursue may need conscious coordination rather than being assumed to match.")
        plain_meaning = " ".join(summary_bits)
        doctrine_bits = []
        if year_map.activated_house_title:
            doctrine_bits.append(
                f"Annual profection activates {year_map.activated_house_title}, making that house and its ruler the main timing frame from one birthday to the next."
            )
        if year_map.solar_return_ascendant:
            doctrine_bits.append(
                "The solar return concentrates the profection year by showing how the storyline becomes more concrete in practice."
            )
        if year_map.fortune_spirit_alignment:
            doctrine_bits.append(
                "Fortune speaks to circumstance and embodiment, while Spirit speaks to chosen direction and intention."
            )
            evidence_items = [
                cls._evidence_item(
                    observation=(
                        f"The profection activates {year_map.activated_house_title or 'the live house'}"
                        + (f" from {year_map.profection_window}." if year_map.profection_window else ".")
                    ),
                    rule="Annual profection sets the primary house and year lord for the current cycle.",
                    interpretation="This identifies the main life area that keeps repeating this year.",
                    score=1,
                    polarity="activation",
                    chart_context="annual_profection",
                )
            ]
        if year_map.solar_return_ascendant:
            evidence_items.append(
                cls._evidence_item(
                    observation=(
                        f"The solar return rises in {year_map.solar_return_ascendant} with the Sun in {cls._house_title_for_id(ontology, year_map.solar_return_sun_house)}."
                    ),
                    rule="Solar return work concentrates the profection year into a more specific atmosphere.",
                    interpretation="This shows how the year's storyline becomes concrete in practice.",
                    score=1,
                    polarity="activation",
                    chart_context="solar_return",
                )
            )
        if year_map.fortune_emphasis and year_map.spirit_emphasis:
            alignment_score = 1 if year_map.fortune_spirit_alignment == "aligned" else -1
            evidence_items.append(
                cls._evidence_item(
                    observation=f"{year_map.fortune_emphasis} {year_map.spirit_emphasis}",
                    rule="Fortune describes bodily or circumstantial emphasis, while Spirit describes intentional and purposive emphasis.",
                    interpretation=(
                        "The two lots reinforce each other."
                        if year_map.fortune_spirit_alignment == "aligned" else
                        "The two lots divide the story between circumstance and intention."
                    ),
                    score=alignment_score,
                    polarity="support" if alignment_score > 0 else "mixed",
                    chart_context="fortune_spirit",
                )
            )
        return InterpretationBlock(
            block_type="year_map",
            title="Current year map",
            section_id="annual_profection",
            summary=plain_meaning,
            citations=cls._resolve_labels([
                "traditional_annual_profection",
                "traditional_solar_return",
                "traditional_fortune_spirit",
            ]),
            confidence="medium",
            evidence_items=evidence_items,
            plain_meaning=plain_meaning,
            traditional_doctrine=" ".join(doctrine_bits) if doctrine_bits else None,
            chart_evidence=[
                line for line in [
                    f"Activated house: {year_map.activated_house_title}" if year_map.activated_house_title else None,
                    f"Lord of the year: {year_map.lord_of_year} in {cls._house_title_for_id(ontology, year_map.lord_of_year_house)}" if year_map.lord_of_year else None,
                    f"Solar return ascendant: {year_map.solar_return_ascendant}" if year_map.solar_return_ascendant else None,
                    f"Fortune and Spirit: {year_map.fortune_spirit_alignment}" if year_map.fortune_spirit_alignment else None,
                ] if line
            ],
            why_this_matters="This gives the main timing frame, so the rest of the reading should be understood as variations on this yearly pattern.",
            confidence_explainer=cls._confidence_explainer("medium"),
            technical_terms=["annual profection", "lord of the year", "solar return", "Fortune", "Spirit"],
            source_tags=cls._resolve_labels([
                "traditional_annual_profection",
                "traditional_solar_return",
                "traditional_fortune_spirit",
            ]),
            display_priority=30,
            repeat_key=(
                f"{year_map.activated_house_title or 'year'}_{year_map.lord_of_year or 'lord'}_{year_map.fortune_spirit_alignment or 'alignment'}"
            ).lower().replace(" ", "_"),
        )

    @classmethod
    def _build_chart_foundation_block(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Optional[InterpretationBlock]:
        context = chart_data.traditional_context
        if not context:
            return None
        asc_ruler = cls._find_planet(chart_data, context.ascendant_ruler) if context.ascendant_ruler else None
        sect_light = cls._find_planet(chart_data, context.sect_light) if context.sect_light else None
        asc_house_meta = cls._house_meta(ontology, 1)
        sect_house_meta = cls._house_meta(ontology, cls._house_number(sect_light.house)) if sect_light and sect_light.house else {}
        plain_meaning = (
            f"This chart begins with {context.ascendant_sign} rising in a {context.sect} chart, so {context.ascendant_ruler} becomes the main planet for how the person meets life, carries the body-level story, and sets basic direction. "
            f"{context.ascendant_ruler} is placed in {asc_ruler.sign if asc_ruler else 'its sign'} {cls._title_from_house(cls._house_meta(ontology, cls._house_number(asc_ruler.house)), asc_ruler.house) if asc_ruler and asc_ruler.house else 'an unknown place'}, which shows where that foundational energy most naturally expresses itself."
        )
        doctrine = (
            f"In traditional astrology, the Ascendant and its ruler set the baseline of body, character, and first response. Sect matters because a {context.sect} chart changes which planets operate more comfortably. "
            f"The sect light, here the {context.sect_light}, adds extra weight to {sect_light.sign if sect_light else 'its'} {cls._title_from_house(sect_house_meta, sect_light.house if sect_light else 'house')} themes."
        )
        return InterpretationBlock(
            block_type="chart_foundation",
            title="Traditional chart foundation",
            section_id="chart_foundation",
            summary=plain_meaning,
            citations=cls._resolve_labels([
                "traditional_sect_condition",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
                "tetrabiblos_sign_expression",
            ]),
            plain_meaning=plain_meaning,
            traditional_doctrine=doctrine,
            chart_evidence=[
                f"Sect: {context.sect}",
                f"Ascendant: {context.ascendant_sign}",
                f"Ascendant ruler: {context.ascendant_ruler} ({cls._planet_condition_phrase(asc_ruler)})" if context.ascendant_ruler else "Ascendant ruler unavailable",
                f"Sect light: {context.sect_light}" if context.sect_light else "Sect light unavailable",
            ],
            life_translation="This is the natal baseline. It often describes how the person naturally acts, recovers, responds, and carries pressure before any yearly timing is added.",
            why_this_matters="It tells you how the person tends to carry any later annual timing or transit pressure.",
            technical_terms=["sect", "Ascendant", "Ascendant ruler"],
            source_tags=cls._resolve_labels([
                "traditional_sect_condition",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
                "tetrabiblos_sign_expression",
            ]),
            display_priority=10,
            repeat_key=f"chart_foundation_{context.ascendant_sign}_{context.ascendant_ruler}".lower(),
        )

    @classmethod
    def _build_fortune_spirit_block(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Optional[InterpretationBlock]:
        context = chart_data.traditional_context
        if not context or not context.fortune or not context.spirit:
            return None
        fortune_house = cls._house_meta(ontology, cls._house_number(context.fortune.house)) if context.fortune.house else {}
        spirit_house = cls._house_meta(ontology, cls._house_number(context.spirit.house)) if context.spirit.house else {}
        alignment, fortune_text, spirit_text = cls._fortune_spirit_alignment(chart_data, ontology)
        alignment_sentence = (
            "Fortune and Spirit are aligned here, so circumstance and intention tend to reinforce each other."
            if alignment == "aligned" else
            "Fortune and Spirit are split here, so what happens around the body and circumstances may not match what the person most intentionally wants to pursue."
        )
        plain_meaning = (
            f"Fortune and Spirit tell two related but different stories. Fortune falls in {context.fortune.sign} {cls._title_from_house(fortune_house, context.fortune.house or 'its house')}, so circumstances gather around {cls._topic_phrase(fortune_house.get('classical_topics', []) or fortune_house.get('modern_topics', []), 3)}. "
            f"Spirit falls in {context.spirit.sign} {cls._title_from_house(spirit_house, context.spirit.house or 'its house')}, so chosen effort gathers around {cls._topic_phrase(spirit_house.get('classical_topics', []) or spirit_house.get('modern_topics', []), 3)}. "
            f"{alignment_sentence}"
        )
        doctrine = (
            "In traditional astrology, Fortune is tied to the body, circumstance, and material conditions, while Spirit is tied to intention, choice, and deliberate action. "
            f"Fortune is ruled by {context.fortune.ruler} ({context.fortune.ruler_strength or 'mixed'}), and Spirit is ruled by {context.spirit.ruler} ({context.spirit.ruler_strength or 'mixed'}), which changes how easily each storyline lands."
        )
        return InterpretationBlock(
            block_type="fortune_spirit",
            title="Fortune and Spirit",
            section_id="fortune_spirit",
            summary=plain_meaning,
            citations=cls._resolve_labels([
                "traditional_fortune_spirit",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
            ]),
            confidence="medium",
            evidence_items=[
                cls._evidence_item(
                    observation=fortune_text or "Fortune marks bodily or circumstantial emphasis.",
                    rule="Fortune shows material, bodily, and circumstantial emphasis in traditional doctrine.",
                    interpretation="This helps locate where circumstances tend to gather and press on the life.",
                    score=1,
                    polarity="activation",
                    chart_context="fortune_spirit",
                ),
                cls._evidence_item(
                    observation=spirit_text or "Spirit marks intentional or purposive emphasis.",
                    rule="Spirit shows intention, action, and purposive direction in traditional doctrine.",
                    interpretation="This helps locate where chosen effort and agency are most likely to gather.",
                    score=1,
                    polarity="activation",
                    chart_context="fortune_spirit",
                ),
                cls._evidence_item(
                    observation=alignment_sentence,
                    rule="The two lots can reinforce one another or split the story between circumstance and intention.",
                    interpretation="The reading should distinguish what is happening around the person from what the person is trying to initiate.",
                    score=1 if alignment == "aligned" else -1,
                    polarity="support" if alignment == "aligned" else "mixed",
                    chart_context="fortune_spirit",
                ),
            ],
            plain_meaning=plain_meaning,
            traditional_doctrine=doctrine,
            chart_evidence=[
                f"Fortune: {context.fortune.sign} {cls._title_from_house(fortune_house, context.fortune.house or 'its house')} ruled by {context.fortune.ruler}",
                f"Spirit: {context.spirit.sign} {cls._title_from_house(spirit_house, context.spirit.house or 'its house')} ruled by {context.spirit.ruler}",
                f"Alignment: {alignment}",
            ],
            life_translation="This can feel like a split between what life is demanding materially and what the person most wants to build intentionally, or a strong convergence when both lots point the same way.",
            why_this_matters="It keeps the reading from flattening circumstance and choice into the same story.",
            confidence_explainer=cls._confidence_explainer("medium"),
            technical_terms=["Fortune", "Spirit", "mixed testimony"],
            source_tags=cls._resolve_labels([
                "traditional_fortune_spirit",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
            ]),
            display_priority=40,
            repeat_key=f"fortune_spirit_{context.fortune.house}_{context.spirit.house}_{alignment}".lower(),
        )

    @classmethod
    def _build_annual_profection_block(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        annual_profection: Optional[AnnualProfectionRecord],
    ) -> Optional[InterpretationBlock]:
        if not annual_profection:
            return None
        house_meta = cls._house_meta(ontology, annual_profection.activated_house)
        topics = cls._topic_phrase(house_meta.get("classical_topics", []) or house_meta.get("modern_topics", []), 3)
        year_lord = cls._find_planet(chart_data, annual_profection.lord_of_year)
        timeframe = ""
        if annual_profection.starts_at and annual_profection.ends_at:
            timeframe = (
                f" The current profection year runs from {annual_profection.starts_at[:10]} to {annual_profection.ends_at[:10]}."
            )
        house_title = cls._title_from_house(house_meta, cls._house_id_from_number(annual_profection.activated_house))
        plain_meaning = (
            f"This is a {house_title} year ruled by {annual_profection.lord_of_year}. In practical terms, the year keeps returning to {topics}. "
            f"{annual_profection.lord_of_year} carries that story from {cls._house_title_for_id(ontology, annual_profection.lord_of_year_house)}, which shows where the yearly theme is most likely to become active or manageable."
            f"{timeframe}"
        )
        doctrine = (
            f"Annual profection moves the chart's focus to a new house each birthday. At age {annual_profection.age}, the activated house is {house_title}, and its ruler becomes the lord of the year. "
            f"Here that ruler is {annual_profection.lord_of_year}, which is {cls._planet_condition_phrase(year_lord)} in {annual_profection.lord_of_year_sign or 'its sign'} {cls._house_title_for_id(ontology, annual_profection.lord_of_year_house)}."
        )
        return InterpretationBlock(
            block_type="annual_profection",
            title="Annual profection",
            section_id="annual_profection",
            summary=plain_meaning,
            citations=cls._resolve_labels([
                "traditional_annual_profection",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
            ]),
            plain_meaning=plain_meaning,
            traditional_doctrine=doctrine,
            chart_evidence=[
                f"Age: {annual_profection.age}",
                f"Activated house: {house_title}",
                f"Lord of the year: {annual_profection.lord_of_year}",
                f"Condition: {cls._planet_condition_phrase(year_lord)}",
            ],
            life_translation="This usually feels like one life area keeps becoming the classroom of the year, while one planet keeps acting like the main timer or gatekeeper.",
            why_this_matters="It explains why one house topic is louder than the rest this year, and why one planet deserves extra attention.",
            technical_terms=["annual profection", "lord of the year"],
            source_tags=cls._resolve_labels([
                "traditional_annual_profection",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
            ]),
            display_priority=20,
            repeat_key=f"annual_profection_{annual_profection.activated_house}_{annual_profection.lord_of_year}".lower(),
        )

    @classmethod
    def _build_solar_return_block(
        cls,
        ontology: Dict,
        solar_return: Optional[SolarReturnRecord],
    ) -> Optional[InterpretationBlock]:
        if not solar_return:
            return None
        sun_house_title = cls._house_title_for_id(ontology, solar_return.sun_house)
        year_lord_house_title = cls._house_title_for_id(ontology, solar_return.year_lord_house)
        angular_text = ", ".join(solar_return.angular_planets[:4]) if solar_return.angular_planets else "no standout angular planets"
        plain_meaning = (
            f"The solar return adds this year's atmosphere. It rises in {solar_return.return_ascendant_sign}, with the Sun landing in {sun_house_title}. "
            f"The profection lord {solar_return.year_lord or 'for the year'} falls in {year_lord_house_title}"
            + (
                f" and is {solar_return.year_lord_strength} there. "
                if solar_return.year_lord
                else ". "
            )
            + f"Angular emphasis gathers around {angular_text}. "
            + (
                f"This return was calculated for {solar_return.return_timestamp[:16].replace('T', ' ')} {solar_return.return_timezone}."
                if solar_return.return_timestamp and solar_return.return_timezone
                else "This return helps concentrate the profection year into a more specific yearly atmosphere."
            )
        )
        doctrine = "Solar return work does not replace the natal chart or the profection year. It shows how the annual storyline is likely to feel and where it becomes concrete."
        return InterpretationBlock(
            block_type="solar_return",
            title="Solar return overlay",
            section_id="solar_return",
            summary=plain_meaning,
            citations=cls._resolve_labels([
                "traditional_solar_return",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
            ]),
            plain_meaning=plain_meaning,
            traditional_doctrine=doctrine,
            chart_evidence=[
                f"Return ascendant: {solar_return.return_ascendant_sign}" if solar_return.return_ascendant_sign else "Return ascendant unavailable",
                f"Sun house: {sun_house_title}",
                f"Year lord house: {year_lord_house_title}",
                f"Angular planets: {angular_text}",
            ],
            why_this_matters="It tells you how the larger yearly pattern is likely to feel on the ground between one birthday and the next.",
            technical_terms=["solar return", "angular"],
            source_tags=cls._resolve_labels([
                "traditional_solar_return",
                "tetrabiblos_house_topic",
                "tetrabiblos_planetary_quality",
            ]),
            display_priority=50,
            repeat_key=f"solar_return_{solar_return.return_ascendant_sign}_{solar_return.year_lord}_{solar_return.sun_house}".lower(),
        )

    @classmethod
    def _build_topic_judgment_blocks(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> List[InterpretationBlock]:
        blocks: List[InterpretationBlock] = []
        for data in cls.build_topic_judgments(chart_data, ontology):
            if data.classification == "supportive":
                opening = "The chart gives clear support here."
            elif data.classification == "difficult":
                opening = "This is the area asking for the most care."
            else:
                opening = "The testimony here is mixed."
            summary = opening + " " + " ".join(
                f"{item.interpretation[:1].upper() + item.interpretation[1:]}"
                + ("" if item.interpretation.endswith(".") else ".")
                for item in data.evidence_items[:3]
            )
            blocks.append(
                InterpretationBlock(
                    block_type="topic_judgment",
                    title=f"{data.title}: {data.classification.capitalize()} testimony",
                    summary=summary,
                    citations=data.citations,
                    topic_key=data.key,
                    confidence=data.confidence,
                    evidence_items=data.evidence_items,
                    caveats=[item.caveat for item in data.evidence_items if item.caveat][:3],
                    plain_meaning=summary,
                    traditional_doctrine="Topical judgment weighs the house, its ruler, occupants, witnesses, lots, and repeated testimony rather than relying on one placement in isolation.",
                    chart_evidence=[item.observation for item in data.evidence_items[:3]],
                    life_translation="This is where the chart is showing repeated support, repeated pressure, or a genuine mix of both.",
                    why_this_matters="Topical judgment tells you where the chart gives the clearest encouragement and where it asks for realism, patience, or repair.",
                    confidence_explainer=cls._confidence_explainer(data.confidence, data.classification),
                    technical_terms=["mixed testimony", "bonification", "maltreatment"],
                    source_tags=data.citations,
                    display_priority=60,
                    repeat_key=f"topic_{data.key}",
                )
            )
        return blocks

    @classmethod
    def _dominant_house_meta(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Tuple[str, Dict, int]:
        houses = cls._house_lookup(ontology)
        occupancy = Counter(planet.house for planet in chart_data.planets)
        if not occupancy:
            return "House1", houses.get(1, {}), 0
        house_id, count = sorted(occupancy.items(), key=lambda item: (-item[1], item[0]))[0]
        return house_id, houses.get(cls._house_number(house_id), {}), count

    @classmethod
    def _element_and_modality_balance(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Dict[str, str]:
        signs = cls._sign_lookup(ontology)
        placements = list(chart_data.planets)
        asc = cls._find_angle(chart_data, "Asc")
        if asc:
            placements.append(PlanetPlacement(id="Asc", sign=asc.sign, sign_degree=asc.sign_degree, longitude=asc.longitude, house="House1", retrograde=False))

        element_counts = Counter()
        modality_counts = Counter()
        for placement in placements:
            sign_meta = signs.get(placement.sign, {})
            if sign_meta.get("element"):
                element_counts[sign_meta["element"]] += 1
            if sign_meta.get("modality"):
                modality_counts[sign_meta["modality"]] += 1

        dominant_element = element_counts.most_common(1)[0][0] if element_counts else "mixed"
        dominant_modality = modality_counts.most_common(1)[0][0] if modality_counts else "mixed"
        return {
            "element": dominant_element,
            "modality": dominant_modality,
        }

    @classmethod
    def _score_levi_current(cls, chart_data: NatalTechnicalChart, current: Dict) -> int:
        trigger_planets = set(current.get("trigger_planets", []))
        trigger_signs = set(current.get("trigger_signs", []))
        trigger_houses = set(current.get("trigger_houses", []))
        trigger_aspects = set(current.get("trigger_aspects", []))

        score = 0
        for planet in chart_data.planets:
            house_number = cls._house_number(planet.house)
            if planet.sign in trigger_signs:
                score += 2
            if house_number in trigger_houses:
                score += 2
            if planet.id in trigger_planets:
                score += 1
                if planet.sign in trigger_signs or house_number in trigger_houses:
                    score += 2

        asc = cls._find_angle(chart_data, "Asc")
        if asc and asc.sign in trigger_signs:
            score += 2

        for aspect in chart_data.aspects[:5]:
            if aspect.type in trigger_aspects:
                score += 2
            if aspect.first in trigger_planets or aspect.second in trigger_planets:
                score += 1

        return score

    @classmethod
    def _select_levi_currents(cls, chart_data: NatalTechnicalChart, ontology: Dict, limit: int = 2) -> List[Dict]:
        currents = cls._levi_lookup(ontology)
        ranked = sorted(currents, key=lambda item: (-cls._score_levi_current(chart_data, item), item.get("display_name", "")))
        return ranked[:limit]

    @classmethod
    def _levi_reason_phrase(cls, chart_data: NatalTechnicalChart, ontology: Dict, current: Dict) -> str:
        houses = cls._house_lookup(ontology)
        reasons: List[str] = []
        trigger_signs = set(current.get("trigger_signs", []))
        trigger_houses = set(current.get("trigger_houses", []))
        trigger_planets = set(current.get("trigger_planets", []))

        for planet in chart_data.planets:
            house_number = cls._house_number(planet.house)
            if planet.id in trigger_planets and len(reasons) < 1:
                reasons.append(f"{planet.id} is a key carrier here")
            if planet.sign in trigger_signs and len(reasons) < 3:
                reasons.append(f"{planet.id} moves through {planet.sign}")
            if house_number in trigger_houses and len(reasons) < 3:
                house_title = houses.get(house_number, {}).get("display_name", planet.house)
                reasons.append(f"{planet.id} lands in the {house_title}")
            if len(reasons) >= 3:
                break

        asc = cls._find_angle(chart_data, "Asc")
        if asc and asc.sign in trigger_signs and len(reasons) < 3:
            reasons.append(f"the Ascendant rises through {asc.sign}")

        return "; ".join(reasons) if reasons else "the chart repeatedly activates this symbolic current"

    @classmethod
    def _build_solar_block(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Optional[InterpretationBlock]:
        sun = cls._find_planet(chart_data, "Sun")
        if not sun:
            return None
        signs = cls._sign_lookup(ontology)
        houses = cls._house_lookup(ontology)
        sign_meta = signs.get(sun.sign, {})
        house_meta = houses.get(cls._house_number(sun.house), {})
        summary = cls._teaching_summary(
            meaning=(
                f"your core style comes through {sun.sign.lower()} energy, which often looks {cls._style_phrase(sign_meta)}"
            ),
            why=(
                f"the Sun describes identity, purpose, and the kind of life direction that feels most like you"
            ),
            real_life=(
                f"you may keep putting serious effort into {cls._topic_phrase(house_meta.get('classical_topics', []) or house_meta.get('modern_topics', []))}, because your Sun is in {cls._title_from_house(house_meta, sun.house)}"
            ),
            watch_for=(
                "putting so much pressure on yourself to perform or succeed that your worth gets tied only to results"
            ),
        )
        return InterpretationBlock(
            block_type="solar_identity",
            title=f"Your core self: {sun.sign} energy in {cls._title_from_house(house_meta, sun.house)}",
            summary=summary,
            citations=cls._resolve_labels([
                "tetrabiblos_planetary_quality",
                "tetrabiblos_sign_expression",
                "tetrabiblos_house_topic",
                "jung_center_identity",
            ]),
        )

    @classmethod
    def _build_lunar_block(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Optional[InterpretationBlock]:
        moon = cls._find_planet(chart_data, "Moon")
        if not moon:
            return None
        signs = cls._sign_lookup(ontology)
        houses = cls._house_lookup(ontology)
        sign_meta = signs.get(moon.sign, {})
        house_meta = houses.get(cls._house_number(moon.house), {})
        summary = cls._teaching_summary(
            meaning=(
                f"your emotional world is colored by {moon.sign.lower()} traits, which can feel {cls._style_phrase(sign_meta)}"
            ),
            why=(
                "the Moon shows how you react, what helps you feel safe, and where your feelings naturally go under stress"
            ),
            real_life=(
                f"your feelings may keep gathering around {cls._topic_phrase(house_meta.get('classical_topics', []) or house_meta.get('modern_topics', []))}, because the Moon is in {cls._title_from_house(house_meta, moon.house)}"
            ),
            watch_for=(
                "falling into emotional habits that feel familiar but make it harder to say what you actually need"
            ),
        )
        return InterpretationBlock(
            block_type="lunar_pattern",
            title=f"Your emotional style: {moon.sign} energy in {cls._title_from_house(house_meta, moon.house)}",
            summary=summary,
            citations=cls._resolve_labels([
                "tetrabiblos_planetary_quality",
                "tetrabiblos_sign_expression",
                "tetrabiblos_house_topic",
            ]),
        )

    @classmethod
    def _build_rising_block(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Optional[InterpretationBlock]:
        asc = cls._find_angle(chart_data, "Asc")
        if not asc:
            return None
        signs = cls._sign_lookup(ontology)
        sign_meta = signs.get(asc.sign, {})
        summary = cls._teaching_summary(
            meaning=(
                f"your rising sign shows how you first come across to other people, and in {asc.sign} that often looks {cls._style_phrase(sign_meta)}"
            ),
            why=(
                "the Ascendant shapes first impressions, outward style, and the way you enter new rooms, relationships, and opportunities"
            ),
            real_life=(
                "people may notice this quality in you before they understand your deeper personality"
            ),
            watch_for=(
                "assuming your first reaction is the whole story, when it may only be your outer style responding quickly"
            ),
        )
        return InterpretationBlock(
            block_type="rising_style",
            title=f"How you come across: rising sign in {asc.sign}",
            summary=summary,
            citations=cls._resolve_labels([
                "tetrabiblos_sign_expression",
                "tetrabiblos_house_topic",
            ]),
        )

    @classmethod
    def _build_ontology_signature_block(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> InterpretationBlock:
        balance = cls._element_and_modality_balance(chart_data, ontology)
        dominant_house_id, dominant_house_meta, count = cls._dominant_house_meta(chart_data, ontology)
        house_topics = cls._topic_phrase(dominant_house_meta.get("classical_topics", []) or dominant_house_meta.get("modern_topics", []), 3)
        balance_phrase = f"the chart has a strong {balance['element']} tone and a {balance['modality']} style"
        summary = cls._teaching_summary(
            meaning=(
                f"{balance_phrase}, and a lot of the chart is concentrated in {cls._title_from_house(dominant_house_meta, dominant_house_id)}"
            ),
            why=(
                "this gives you the big picture of how the whole chart behaves, instead of looking at one placement at a time"
            ),
            real_life=(
                f"life may keep pulling you back toward {house_topics}, because that is where several parts of the chart are concentrated"
            ),
            watch_for=(
                "over-identifying with one area of life and forgetting that the rest of the chart still matters too"
            ),
        )
        return InterpretationBlock(
            block_type="ontology_signature",
            title="The big pattern of your chart",
            summary=summary,
            citations=cls._resolve_labels([
                "tetrabiblos_sign_expression",
                "tetrabiblos_house_topic",
                "levi_symbolic_correspondence",
            ]),
        )

    @classmethod
    def _build_levi_current_block(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Optional[InterpretationBlock]:
        currents = cls._select_levi_currents(chart_data, ontology, limit=1)
        if not currents:
            return None
        current = currents[0]
        citations = ["levi_kabbalistic_correspondence", *current.get("source_lens_tags", [])]
        current_name = current.get("display_name", "symbolic correspondence")
        summary = cls._teaching_summary(
            meaning=(
                f"the strongest symbolic current in this chart is {current_name}. {current.get('narrative', '')}".strip()
            ),
            why=(
                "this helps connect separate placements into one larger story or theme"
            ),
            real_life=(
                f"this pattern stands out because {cls._levi_reason_phrase(chart_data, ontology, current)}"
            ),
            watch_for=(
                "treating symbolism like fate instead of using it as a lens for better understanding"
            ),
        )
        return InterpretationBlock(
            block_type="levi_current",
            title=f"Main symbolic theme: {current.get('display_name', 'Correspondence')}",
            summary=summary,
            citations=cls._resolve_labels(citations),
        )

    @classmethod
    def _build_house_concentration_blocks(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> List[InterpretationBlock]:
        houses = cls._house_lookup(ontology)
        occupancy = Counter(planet.house for planet in chart_data.planets)
        ranked_houses = sorted(occupancy.items(), key=lambda item: (-item[1], item[0]))[:2]
        blocks: List[InterpretationBlock] = []
        for house_id, count in ranked_houses:
            house_meta = houses.get(cls._house_number(house_id), {})
            topics = cls._topic_phrase(house_meta.get("classical_topics", []) or house_meta.get("modern_topics", []), 3)
            blocks.append(
                InterpretationBlock(
                    block_type="house_focus",
                    title=f"Where life is especially concentrated: {cls._title_from_house(house_meta, house_id)}",
                    summary=cls._teaching_summary(
                        meaning=f"{count} major planets gather in this house, so this part of life is heavily emphasized",
                        why="when many planets gather in one house, that life area becomes a repeated classroom",
                        real_life=f"themes around {topics} may keep showing up in work, relationships, decisions, and turning points",
                        watch_for="assuming the repeated lesson means you are failing, when it may simply be one of your main growth areas",
                    ),
                    citations=cls._resolve_labels(["tetrabiblos_house_topic"]),
                )
            )
        return blocks

    @classmethod
    def _build_major_aspect_blocks(cls, chart_data: NatalTechnicalChart, ontology: Dict, include_jungian: bool) -> List[InterpretationBlock]:
        aspects = cls._aspect_lookup(ontology)
        planets = cls._planet_lookup(ontology)
        blocks: List[InterpretationBlock] = []
        for aspect in chart_data.aspects[:3]:
            aspect_meta = aspects.get(aspect.type, {})
            first_meta = planets.get(aspect.first, {})
            second_meta = planets.get(aspect.second, {})
            citations = ["tetrabiblos_aspect_relation"]
            if include_jungian and aspect.type == "Square":
                citations.append("jung_tension_of_opposites")
            elif include_jungian and aspect.type == "Opposition":
                citations.append("jung_projection_mirror")
            blocks.append(
                InterpretationBlock(
                    block_type="major_aspect",
                    title=f"A strong inner pattern: {aspect.first} {aspect.type.lower()} {aspect.second}",
                    summary=cls._teaching_summary(
                        meaning=(
                            f"{aspect.first} and {aspect.second} are in a strong {aspect.type.lower()} relationship, linking {cls._topic_phrase(first_meta.get('core_topics', []))} with {cls._topic_phrase(second_meta.get('core_topics', []))}"
                        ),
                        why=(
                            "major aspects show how different parts of your personality cooperate, clash, or demand balance"
                        ),
                        real_life=(
                            f"you may feel this as a repeated pattern where one need pulls against another; this pattern is fairly close, with a distance from exact of {aspect.orb:.2f} degrees"
                        ),
                        watch_for=(
                            "thinking inner tension means something is wrong, when often it is the chart asking for maturity and integration"
                        ),
                    ),
                    citations=cls._resolve_labels(citations),
                )
            )
        return blocks

    @classmethod
    def _build_planet_emphasis_block(cls, chart_data: NatalTechnicalChart, ontology: Dict, planet_name: str) -> Optional[InterpretationBlock]:
        planet = cls._find_planet(chart_data, planet_name)
        if not planet:
            return None
        planets = cls._planet_lookup(ontology)
        signs = cls._sign_lookup(ontology)
        houses = cls._house_lookup(ontology)
        planet_meta = planets.get(planet.id, {})
        sign_meta = signs.get(planet.sign, {})
        house_meta = houses.get(cls._house_number(planet.house), {})
        core_topics = cls._topic_phrase(planet_meta.get("core_topics", []))
        summary = cls._teaching_summary(
            meaning=(
                f"{planet.id} shows how you handle {core_topics}, and in {planet.sign} it tends to work in a {cls._style_phrase(sign_meta)} way"
            ),
            why=(
                f"this tells you how the {planet.id.lower()} part of your personality operates"
            ),
            real_life=(
                f"you will especially notice it in {cls._topic_phrase(house_meta.get('classical_topics', []) or house_meta.get('modern_topics', []))}, because {planet.id} sits in {cls._title_from_house(house_meta, planet.house)}"
            ),
            watch_for=(
                f"using the lower expression of {planet.id.lower()} when pressure rises, instead of its wiser and steadier side"
            ),
        )
        return InterpretationBlock(
            block_type="planet_emphasis",
            title=f"How your {planet.id.lower()} works: {planet.sign} energy in {cls._title_from_house(house_meta, planet.house)}",
            summary=summary,
            citations=cls._resolve_labels([
                "tetrabiblos_planetary_quality",
                "tetrabiblos_sign_expression",
                "tetrabiblos_house_topic",
            ]),
        )

    @classmethod
    def _build_planet_emphasis_blocks(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> List[InterpretationBlock]:
        blocks: List[InterpretationBlock] = []
        for planet_name in cls.PLANET_SEQUENCE:
            block = cls._build_planet_emphasis_block(chart_data, ontology, planet_name)
            if block:
                blocks.append(block)
        return blocks

    @classmethod
    def _build_jungian_mapping_blocks(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        include_red_book_prompts: bool,
    ) -> List[InterpretationBlock]:
        mappings = ontology.get("jungian_mappings", [])
        blocks: List[InterpretationBlock] = []

        venus = cls._find_planet(chart_data, "Venus")
        saturn = cls._find_planet(chart_data, "Saturn")
        moon = cls._find_planet(chart_data, "Moon")
        mars = cls._find_planet(chart_data, "Mars")
        sun = cls._find_planet(chart_data, "Sun")

        matches: List[str] = []
        if venus and saturn:
            conjunction = cls._find_aspect(chart_data, "Venus", "Saturn", "Conjunction")
            seventh_house = venus.house == "House7" or saturn.house == "House7"
            if conjunction and seventh_house:
                matches.append("saturn_venus_7th")

        if moon and mars and cls._find_aspect(chart_data, "Moon", "Mars", "Square"):
            matches.append("mars_moon_square")

        if sun and saturn and cls._find_aspect(chart_data, "Sun", "Saturn", "Opposition"):
            matches.append("sun_saturn_opposition")

        mercury = cls._find_planet(chart_data, "Mercury")
        jupiter = cls._find_planet(chart_data, "Jupiter")

        if mercury and saturn and cls._find_aspect(chart_data, "Mercury", "Saturn", "Conjunction"):
            matches.append("mercury_saturn_conjunction")

        if venus and mars and cls._find_aspect(chart_data, "Venus", "Mars", "Opposition"):
            matches.append("venus_mars_opposition")

        if moon and jupiter and cls._find_aspect(chart_data, "Moon", "Jupiter", "Trine"):
            matches.append("moon_jupiter_trine")

        if mars and saturn and cls._find_aspect(chart_data, "Mars", "Saturn", "Conjunction"):
            matches.append("mars_saturn_conjunction")

        for mapping_id in matches:
            mapping = next((item for item in mappings if item.get("mapping_id") == mapping_id), None)
            if not mapping:
                continue
            citations = ["tetrabiblos_aspect_relation"]
            if mapping_id == "mars_moon_square":
                citations.append("jung_tension_of_opposites")
            elif mapping_id in {"mercury_saturn_conjunction", "moon_jupiter_trine"}:
                citations.append("jung_complex_activation")
            elif mapping_id in {"venus_mars_opposition", "mars_saturn_conjunction"}:
                citations.append("jung_shadow_integration")
            else:
                citations.append("jung_projection_mirror")
            if include_red_book_prompts:
                citations.append("red_book_imaginal_prompt")
            blocks.append(
                InterpretationBlock(
                    block_type="jungian_trigger",
                    title="A psychological growth pattern",
                    summary=cls._teaching_summary(
                        meaning=(
                            f"this chart repeats a pattern that often carries a psychological lesson, especially around {cls._topic_phrase(mapping.get('jungian_core_tags', []), 3)}"
                        ),
                        why=(
                            "these patterns often show where growth happens through tension, reflection, or relationship mirrors"
                        ),
                        real_life=(
                            f"you may notice this pattern through situations involving {cls._topic_phrase(mapping.get('classical_tags', []), 3)}"
                        ),
                        watch_for=(
                            f"missing the growth task here: {mapping.get('developmental_task', 'Hold the tension carefully.')}"
                        ),
                    ),
                    citations=cls._resolve_labels(citations),
                )
            )
        return blocks

    @classmethod
    def _build_red_book_block(cls, chart_data: NatalTechnicalChart, ontology: Dict) -> Optional[InterpretationBlock]:
        moon = cls._find_planet(chart_data, "Moon")
        if not moon:
            return None
        houses = cls._house_lookup(ontology)
        house_meta = houses.get(cls._house_number(moon.house), {})
        topics = cls._topic_phrase(house_meta.get("classical_topics", []) or house_meta.get("modern_topics", []))
        summary = cls._teaching_summary(
            meaning=f"dreams, images, and repeated moods around {topics} may be carrying useful meaning",
            why="this gives you a reflective way to learn from the chart instead of only analyzing it intellectually",
            real_life="you might notice a repeated symbol, memory, or emotional scene showing up in journaling or dreams",
            watch_for="forcing a dramatic interpretation too quickly instead of observing the pattern first",
        )
        return InterpretationBlock(
            block_type="imaginal_prompt",
            title="A reflective journaling prompt",
            summary=summary,
            citations=cls._resolve_labels(["red_book_imaginal_prompt"]),
        )

    @classmethod
    def build_prediction_cards(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        include_jungian: bool,
        include_red_book_prompts: bool,
        annual_profection: Optional[AnnualProfectionRecord] = None,
        solar_return: Optional[SolarReturnRecord] = None,
    ) -> List[PredictionCard]:
        if chart_data.traditional_context:
            topic_data = cls.build_topic_judgments(chart_data, ontology)
            year_map = cls.build_year_map_record(chart_data, ontology, annual_profection, solar_return)
            strongest_topic = max(topic_data, key=lambda item: item.score)
            hardest_topic = min(topic_data, key=lambda item: item.score)
            if hardest_topic.key == strongest_topic.key and len(topic_data) > 1:
                hardest_topic = sorted(topic_data, key=lambda item: item.score)[1]

            first_summary = "The traditional timing anchor is not available yet."
            first_timeframe = "Current year"
            opportunities = ["Track repeated themes instead of isolated events."]
            cautions = ["Do not treat one activation as the whole life story."]
            rituals = ["Keep a brief log of repeated events in the activated house."]
            if year_map:
                first_timeframe = year_map.profection_window or "Current profection year"
                first_summary = (
                    f"The year activates {year_map.activated_house_title or 'the live house'}, centering {cls._topic_phrase(year_map.activated_topics, 3)}. "
                    f"{year_map.lord_of_year} carries the year from {cls._house_title_for_id(ontology, year_map.lord_of_year_house)}, where it is {year_map.lord_of_year_condition or 'mixed'}."
                    + (
                        f" The solar return rises in {year_map.solar_return_ascendant} and places the year lord in {cls._house_title_for_id(ontology, year_map.solar_return_year_lord_house)}."
                        if year_map.solar_return_ascendant else
                        ""
                    )
                )
                opportunities = [
                    f"Act where {cls._topic_phrase(year_map.activated_topics, 3)} are already asking for attention.",
                    year_map.guidance or "Use the year lord deliberately instead of waiting for events to force the theme.",
                ]
                cautions = [
                    "Do not universalize the year lord into every life area.",
                    "Read the solar return as a concentration of the year, not a replacement for the natal baseline.",
                ]
                rituals = [
                    "Review what keeps repeating since the last birthday.",
                    "Track the house of the year lord whenever a major event lands.",
                ]

            alignment, fortune_text, spirit_text = cls._fortune_spirit_alignment(chart_data, ontology)
            fortune_summary = (
                f"{fortune_text} {spirit_text} "
                + (
                    "Fortune and Spirit are reinforcing each other, so circumstance and intention are telling a similar story."
                    if alignment == "aligned" else
                    "Fortune and Spirit are split, so the most available path may not be the most intentional one."
                )
                if fortune_text and spirit_text else
                "Fortune and Spirit are not available yet."
            )
            fortune_opportunities = [
                "Separate what is happening around the body or circumstances from what you are deliberately trying to build.",
                "Notice whether the same house is being emphasized by both lots or whether the story is divided.",
            ]
            fortune_cautions = [
                "Do not confuse circumstantial momentum with genuine commitment.",
                "Do not assume tension between Fortune and Spirit means failure; it often means divided emphasis.",
            ]
            fortune_rituals = [
                "Write one sentence for what life is doing to you and one sentence for what you are intentionally choosing.",
                "Compare those two sentences before making a big decision.",
            ]

            return [
                PredictionCard(
                    key="current_year_map",
                    title="Current year map",
                    timeframe=first_timeframe,
                    summary=first_summary,
                    opportunities=opportunities,
                    cautions=cautions,
                    rituals=rituals,
                    citations=cls._resolve_labels([
                        "traditional_annual_profection",
                        "traditional_solar_return",
                        "traditional_fortune_spirit",
                        "tetrabiblos_house_topic",
                        "tetrabiblos_planetary_quality",
                    ]),
                ),
                PredictionCard(
                    key="fortune_spirit_split",
                    title="How Fortune and Spirit divide the story",
                    timeframe=first_timeframe,
                    summary=fortune_summary,
                    opportunities=fortune_opportunities,
                    cautions=fortune_cautions,
                    rituals=fortune_rituals,
                    citations=cls._resolve_labels([
                        "traditional_fortune_spirit",
                        "tetrabiblos_house_topic",
                        "tetrabiblos_planetary_quality",
                    ]),
                ),
                PredictionCard(
                    key=f"topic_{strongest_topic.key}_{hardest_topic.key}",
                    title=f"Where the testimony leans: {strongest_topic.title} and {hardest_topic.title}",
                    timeframe="Watch this threshold",
                    summary=(
                        f"The easiest support appears in {strongest_topic.title.lower()}, while the greatest strain concentrates in {hardest_topic.title.lower()}. "
                        + " ".join(f"{item.interpretation}." for item in strongest_topic.evidence_items[:1])
                        + " "
                        + " ".join(f"{item.interpretation}." for item in hardest_topic.evidence_items[:1])
                    ),
                    opportunities=[
                        "Prioritize the area where support is already present instead of fighting the whole chart at once.",
                        "Handle the stressed topic early, while it is still manageable.",
                    ],
                    cautions=[
                        "Do not mistake one stressed topic for total bad fate.",
                        "Repeated strain is a signal to change method, pacing, or support.",
                    ],
                    rituals=[
                        "Write down one supported move and one strain point for the same week.",
                        "Name the recurring problem clearly before trying to solve it symbolically.",
                    ],
                    citations=sorted({
                        *strongest_topic.citations,
                        *hardest_topic.citations,
                    }),
                ),
            ]

        currents = cls._select_levi_currents(chart_data, ontology, limit=2)
        primary_current = currents[0] if currents else None
        secondary_current = currents[1] if len(currents) > 1 else primary_current
        signs = cls._sign_lookup(ontology)
        sun = cls._find_planet(chart_data, "Sun")
        moon = cls._find_planet(chart_data, "Moon")
        asc = cls._find_angle(chart_data, "Asc")
        dominant_house_id, dominant_house_meta, _ = cls._dominant_house_meta(chart_data, ontology)
        dominant_house_title = cls._title_from_house(dominant_house_meta, dominant_house_id)
        dominant_topics = cls._topic_phrase(dominant_house_meta.get("classical_topics", []) or dominant_house_meta.get("modern_topics", []), 3)
        strongest_aspect = chart_data.aspects[0] if chart_data.aspects else None
        balance = cls._element_and_modality_balance(chart_data, ontology)

        first_citations = ["tetrabiblos_house_topic", "tetrabiblos_aspect_relation"]
        if primary_current:
            first_citations.extend(primary_current.get("source_lens_tags", []))

        second_citations = ["tetrabiblos_sign_expression", "tetrabiblos_house_topic", "levi_symbolic_correspondence"]
        if include_jungian:
            second_citations.append("jung_center_identity")

        third_citations = ["tetrabiblos_house_topic"]
        if include_red_book_prompts:
            third_citations.append("red_book_imaginal_prompt")
        if secondary_current:
            third_citations.extend(secondary_current.get("source_lens_tags", []))

        first_summary = (
            f"For the next 30 days, the clearest focus is {dominant_house_title.lower()} matters: {dominant_topics}. "
            "This is where life is asking for steady attention right now."
        )
        if strongest_aspect:
            first_summary += f" The immediate weather is colored by {strongest_aspect.first} {strongest_aspect.type.lower()} {strongest_aspect.second}."

        second_summary = (
            f"Over the next few months, growth comes from using your chart's natural style: {balance['element']} and {balance['modality']}. "
            f"That means progress is more likely when you work with your natural rhythm instead of against it, especially around {dominant_topics}."
        )
        if asc:
            asc_meta = signs.get(asc.sign, {})
            second_summary += f" Let the outer approach stay {cls._style_phrase(asc_meta)} rather than defensive or vague."

        third_summary = (
            f"Pay attention to repeating feelings and situations around {primary_current.get('prediction_focus', dominant_topics) if primary_current else dominant_topics}. "
            "Those repeats are usually teaching you where the chart is active, not predicting disaster."
        )

        return [
            PredictionCard(
                key="natal_near_term",
                title="What is most active right now",
                timeframe="Next 30 days",
                summary=first_summary,
                opportunities=[
                    f"Advance one concrete move in {dominant_topics}.",
                    f"Use {primary_current.get('themes', ['discipline'])[0]} as a strategic advantage." if primary_current else "Use disciplined focus as a strategic advantage.",
                ],
                cautions=[
                    primary_current.get("shadow_watch", ["scattered effort"])[0] if primary_current else "scattered effort",
                    "Do not let a strong mood harden into a fixed fate story.",
                ],
                rituals=(primary_current.get("ritual_actions", [])[:2] if primary_current else ["Write down the one commitment that matters most this month."]),
                citations=cls._resolve_labels(first_citations),
            ),
            PredictionCard(
                key="natal_growth_arc",
                title="Where growth is asking for your attention",
                timeframe="Next 90 days",
                summary=second_summary,
                opportunities=[
                    f"Make the {sun.sign if sun else balance['element']} style visible in your work.",
                    f"Build momentum around {dominant_house_title.lower()} themes before novelty scatters it.",
                ],
                cautions=[
                    secondary_current.get("shadow_watch", ["overreach"])[0] if secondary_current else "overreach",
                    "Avoid trading depth for speed.",
                ],
                rituals=(secondary_current.get("ritual_actions", [])[:2] if secondary_current else ["Review what is actually growing and what is merely busy."]),
                citations=cls._resolve_labels(second_citations),
            ),
            PredictionCard(
                key="natal_threshold",
                title="What to notice and learn from",
                timeframe="Watch this threshold",
                summary=third_summary,
                opportunities=[
                    f"Let {moon.sign if moon else 'lunar'} feelings become information before they become reaction.",
                    "Treat the recurring symbol as a prompt for action, not just interpretation.",
                ],
                cautions=[
                    primary_current.get("shadow_watch", ["projection"])[-1] if primary_current else "projection",
                    "Do not confuse atmosphere with evidence.",
                ],
                rituals=(primary_current.get("ritual_actions", ["Keep a one-page omen log for the week."])[1:3] if primary_current and len(primary_current.get("ritual_actions", [])) > 1 else ["Keep a one-page omen log for the week."]),
                citations=cls._resolve_labels(third_citations),
            ),
        ]

    @classmethod
    def build_planetary_fallback_blocks(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        include_jungian: bool,
        include_red_book_prompts: bool,
    ) -> List[InterpretationBlock]:
        blocks: List[InterpretationBlock] = []
        sun = cls._find_planet(chart_data, "Sun")
        moon = cls._find_planet(chart_data, "Moon")
        if sun:
            blocks.append(
                InterpretationBlock(
                    block_type="solar_identity",
                    title=f"Simple mode: your core self in {sun.sign}",
                    summary=cls._teaching_summary(
                        meaning=f"without an exact birth time, the safest starting point is the Sun in {sun.sign}",
                        why="the Sun still gives a reliable baseline for personality and direction even when timing data is incomplete",
                        real_life="you can still learn something useful about your style and motivation without pretending the chart is more exact than it is",
                        watch_for="making house or angle claims before the birth time is verified",
                    ),
                    citations=cls._resolve_labels(["tetrabiblos_planetary_quality", "tetrabiblos_sign_expression"]),
                )
            )
        if moon:
            blocks.append(
                InterpretationBlock(
                    block_type="lunar_pattern",
                    title=f"Simple mode: your emotional style in {moon.sign}",
                    summary=cls._teaching_summary(
                        meaning=f"the Moon in {moon.sign} still tells us a lot about emotional style",
                        why="emotional patterns are often still readable even when birth time is not exact",
                        real_life="you may recognize the emotional tone, but not yet the precise life area where it lands",
                        watch_for="treating an incomplete chart like a fully timed one",
                    ),
                    citations=cls._resolve_labels(["tetrabiblos_planetary_quality", "tetrabiblos_sign_expression"]),
                )
            )
        for aspect in chart_data.aspects[:3]:
            citations = ["tetrabiblos_aspect_relation"]
            if include_jungian and aspect.type in {"Square", "Opposition"}:
                citations.append("jung_tension_of_opposites")
            blocks.append(
                InterpretationBlock(
                    block_type="major_aspect",
                    title=f"Simple mode: {aspect.first} {aspect.type.lower()} {aspect.second}",
                    summary=cls._teaching_summary(
                        meaning=f"{aspect.first} {aspect.type} {aspect.second} is still readable even without exact house data",
                        why="planet-to-planet patterns can still teach us something real about the chart's basic structure",
                        real_life="you may notice this as a repeating personality pattern even before the full chart is timed",
                        watch_for="acting more certain than the data allows",
                    ),
                    citations=cls._resolve_labels(citations),
                )
            )
        if include_red_book_prompts:
            blocks.append(
                InterpretationBlock(
                    block_type="imaginal_prompt",
                    title="Simple mode reflective prompt",
                    summary=cls._teaching_summary(
                        meaning="the strongest mood, dream image, or repeating symbol may point toward the active planets",
                        why="this gives you a usable reflective method while the chart remains incomplete",
                        real_life="a repeated symbol or feeling may help you identify the tone of the moment",
                        watch_for="turning every symbol into certainty instead of a clue",
                    ),
                    citations=cls._resolve_labels(["red_book_imaginal_prompt"]),
                )
            )
        return blocks

    @classmethod
    def build_planetary_fallback_prediction_cards(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        include_red_book_prompts: bool,
    ) -> List[PredictionCard]:
        sun = cls._find_planet(chart_data, "Sun")
        moon = cls._find_planet(chart_data, "Moon")
        strongest_aspect = chart_data.aspects[0] if chart_data.aspects else None
        first_summary = (
            f"Use the Sun in {sun.sign if sun else 'its sign'} as the clearest short-term guide. "
            "This simpler mode stays with the parts of the chart we can trust without an exact birth time."
        )
        if strongest_aspect:
            first_summary += f" The clearest current aspect is {strongest_aspect.first} {strongest_aspect.type.lower()} {strongest_aspect.second}."

        second_summary = (
            f"Watch {moon.sign if moon else 'lunar'} moods for clues, but treat them as emotional weather rather than exact timing until the birth time is confirmed."
        )

        third_summary = "The next accuracy upgrade is simple: find the birth record, then rerun the chart with full houses, angles, and better timing." 

        return [
            PredictionCard(
                key="planetary_fallback_core",
                title="What is clear even in simple mode",
                timeframe="Usable now",
                summary=first_summary,
                opportunities=[
                    "Work from the clearest planetary tone first.",
                    "Use the fallback mode for temperament, not house-specific timing calls.",
                ],
                cautions=["overclaiming", "treating a fallback chart like a timed rectification"],
                rituals=["Note what remains stable across multiple retellings of the story."],
                citations=cls._resolve_labels(["tetrabiblos_planetary_quality", "tetrabiblos_aspect_relation"]),
            ),
            PredictionCard(
                key="planetary_fallback_mood",
                title="Emotional weather",
                timeframe="Watch this week",
                summary=second_summary,
                opportunities=["Use mood as information.", "Record repeated images or reactions before interpreting them."],
                cautions=["projection", "mistaking atmosphere for exact timing"],
                rituals=(
                    ["Keep a short dream or omen log for seven days."]
                    if include_red_book_prompts else
                    ["Keep a short mood log for seven days."]
                ),
                citations=cls._resolve_labels(["tetrabiblos_sign_expression", *( ["red_book_imaginal_prompt"] if include_red_book_prompts else [] )]),
            ),
            PredictionCard(
                key="planetary_fallback_upgrade",
                title="How to improve accuracy",
                timeframe="Before relying on house timing",
                summary=third_summary,
                opportunities=["Locate the birth certificate, hospital record, or family record."],
                cautions=["false certainty"],
                rituals=["Rerun the chart once the exact time is confirmed."],
                citations=cls._resolve_labels(["tetrabiblos_house_topic"]),
            ),
        ]

    @classmethod
    def build_planetary_fallback_reading_section(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        include_jungian: bool,
        include_red_book_prompts: bool,
    ) -> ReadingSection:
        blocks = cls.build_planetary_fallback_blocks(chart_data, ontology, include_jungian, include_red_book_prompts)
        cards = cls.build_planetary_fallback_prediction_cards(chart_data, ontology, include_red_book_prompts)
        sun = cls._find_planet(chart_data, "Sun")
        moon = cls._find_planet(chart_data, "Moon")
        return ReadingSection(
            headline=f"Simple natal guide: {sun.sign if sun else 'solar'} core, {moon.sign if moon else 'lunar'} emotional tone.",
            practical_meaning=blocks[0].summary if blocks else "Planetary fallback is available.",
            life_translation=blocks[1].summary if len(blocks) > 1 else "This mode keeps to the stable planetary layer.",
            guidance=cards[0].summary if cards else "Use the stable planetary layer first until the birth time is confirmed.",
            prompt=(blocks[-1].summary if include_red_book_prompts and blocks else None),
            timing_focus="Timing stays general in fallback mode until the birth time is verified.",
            ritual_focus=cards[1].rituals[0] if len(cards) > 1 and cards[1].rituals else None,
            oracle="The Ark is speaking in simplified fallback mode until the birth time is exact.",
        )

    @classmethod
    def build_blocks(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        include_jungian: bool,
        include_red_book_prompts: bool,
        annual_profection: Optional[AnnualProfectionRecord] = None,
        solar_return: Optional[SolarReturnRecord] = None,
    ) -> List[InterpretationBlock]:
        if chart_data.traditional_context:
            blocks: List[InterpretationBlock] = []
            year_map = cls.build_year_map_record(chart_data, ontology, annual_profection, solar_return)
            for block in [
                cls._build_chart_foundation_block(chart_data, ontology),
                cls._build_fortune_spirit_block(chart_data, ontology),
                cls._build_annual_profection_block(chart_data, ontology, annual_profection),
                cls._build_solar_return_block(ontology, solar_return),
                cls._build_year_map_block(year_map, ontology),
            ]:
                if block:
                    blocks.append(block)
            blocks.extend(cls._build_topic_judgment_blocks(chart_data, ontology))
            if include_jungian:
                blocks.extend(cls._build_jungian_mapping_blocks(chart_data, ontology, include_red_book_prompts))
            if include_red_book_prompts:
                red_book_block = cls._build_red_book_block(chart_data, ontology)
                if red_book_block:
                    blocks.append(red_book_block)
            return blocks

        blocks: List[InterpretationBlock] = []
        for block in [
            cls._build_solar_block(chart_data, ontology),
            cls._build_lunar_block(chart_data, ontology),
            cls._build_rising_block(chart_data, ontology),
        ]:
            if block:
                blocks.append(block)

        blocks.append(cls._build_ontology_signature_block(chart_data, ontology))
        if include_jungian:
            levi_block = cls._build_levi_current_block(chart_data, ontology)
            if levi_block:
                levi_block.title = levi_block.title.replace("Main symbolic theme", "Supplemental symbolic theme", 1)
                blocks.append(levi_block)

        blocks.extend(cls._build_house_concentration_blocks(chart_data, ontology))
        blocks.extend(cls._build_major_aspect_blocks(chart_data, ontology, include_jungian))
        blocks.extend(cls._build_planet_emphasis_blocks(chart_data, ontology))

        if include_jungian:
            blocks.extend(cls._build_jungian_mapping_blocks(chart_data, ontology, include_red_book_prompts))

        if include_red_book_prompts:
            red_book_block = cls._build_red_book_block(chart_data, ontology)
            if red_book_block:
                blocks.append(red_book_block)
        return blocks

    @classmethod
    def build_reading_section(
        cls,
        chart_data: NatalTechnicalChart,
        ontology: Dict,
        include_jungian: bool,
        include_red_book_prompts: bool,
        annual_profection: Optional[AnnualProfectionRecord] = None,
        solar_return: Optional[SolarReturnRecord] = None,
    ) -> ReadingSection:
        blocks = cls.build_blocks(
            chart_data,
            ontology,
            include_jungian,
            include_red_book_prompts,
            annual_profection=annual_profection,
            solar_return=solar_return,
        )
        prediction_cards = cls.build_prediction_cards(
            chart_data,
            ontology,
            include_jungian,
            include_red_book_prompts,
            annual_profection=annual_profection,
            solar_return=solar_return,
        )
        if chart_data.traditional_context:
            context = chart_data.traditional_context
            year_map = cls.build_year_map_record(chart_data, ontology, annual_profection, solar_return)
            foundation_block = next((block for block in blocks if block.block_type == "chart_foundation"), None)
            fortune_spirit_block = next((block for block in blocks if block.block_type == "fortune_spirit"), None)
            solar_return_block = next((block for block in blocks if block.block_type == "solar_return"), None)
            year_map_block = next((block for block in blocks if block.block_type == "year_map"), None)
            prompt = None
            if include_red_book_prompts:
                red_book_block = next((block for block in blocks if block.block_type == "imaginal_prompt"), None)
                prompt = red_book_block.summary if red_book_block else "Record symbols before interpreting them."
            oracle = None
            if annual_profection and solar_return and solar_return.year_lord:
                oracle = (
                    f"The Ark names {solar_return.year_lord.lower()} as the planet carrying the year"
                    + (
                        f" and reads Fortune and Spirit as {year_map.fortune_spirit_alignment}."
                        if year_map and year_map.fortune_spirit_alignment else
                        "."
                    )
                )
            elif annual_profection:
                oracle = (
                    f"The Ark names {annual_profection.lord_of_year.lower()} as the planet carrying the current profection year."
                )
            elif context.ascendant_ruler:
                oracle = f"The Ark starts with {context.ascendant_ruler.lower()} because it rules the Ascendant."
            headline = f"{context.ascendant_sign} rising sets the baseline, and {context.ascendant_ruler} carries the chart's first response to life."
            if year_map and year_map.activated_house_title and year_map.lord_of_year:
                headline = (
                    f"This is a {year_map.activated_house_title} year ruled by {year_map.lord_of_year}."
                )
            return ReadingSection(
                headline=headline,
                practical_meaning=year_map_block.summary if year_map_block else (foundation_block.summary if foundation_block else "Traditional chart structure is available."),
                life_translation=fortune_spirit_block.summary if fortune_spirit_block else (solar_return_block.summary if solar_return_block else "Fortune and Spirit are available for contextual judgment."),
                guidance=prediction_cards[0].summary if prediction_cards else "Read repeated testimony before making a strong claim.",
                prompt=prompt,
                timing_focus=prediction_cards[0].summary if prediction_cards else None,
                ritual_focus="; ".join(prediction_cards[0].rituals[:2]) if prediction_cards else None,
                oracle=oracle,
            )

        sun = cls._find_planet(chart_data, "Sun")
        moon = cls._find_planet(chart_data, "Moon")
        asc = cls._find_angle(chart_data, "Asc")

        practical = blocks[0].summary if len(blocks) > 0 else "Calculated natal structure is available."

        mapping_block = next((block for block in blocks if block.block_type == "jungian_trigger"), None)
        lunar_block = next((block for block in blocks if block.block_type == "lunar_pattern"), None)
        levi_block = next((block for block in blocks if block.block_type == "levi_current"), None)
        aspect_block = next((block for block in blocks if block.block_type == "major_aspect"), None)

        if include_jungian and mapping_block:
            life_translation = mapping_block.summary
        elif lunar_block:
            life_translation = lunar_block.summary
        elif aspect_block:
            life_translation = aspect_block.summary
        elif levi_block:
            life_translation = levi_block.summary
        else:
            life_translation = "The chart's inner patterns can be translated into lived experience without overriding the structural reading."

        if prediction_cards:
            guidance = prediction_cards[0].summary
        elif aspect_block:
            guidance = aspect_block.summary
        else:
            guidance = "Use the chart as a guide for understanding and action, not as a script that removes choice."

        prompt = None
        if include_red_book_prompts:
            red_book_block = next((block for block in blocks if block.block_type == "imaginal_prompt"), None)
            prompt = red_book_block.summary if red_book_block else "Record dreams before interpreting them."

        ritual_focus = "; ".join(prediction_cards[0].rituals[:2]) if prediction_cards else None
        oracle = None
        if levi_block:
            oracle = f"The Ark names this chart's supplemental symbolic theme as {levi_block.title.replace('Supplemental symbolic theme: ', '').lower()}."

        headline = (
            f"Your chart begins with {cls._with_article(sun.sign if sun else 'solar')} core, "
            f"{cls._with_article(moon.sign if moon else 'lunar')} emotional life, and {cls._with_article(asc.sign if asc else 'rising')} way of meeting the world."
        )

        return ReadingSection(
            headline=headline,
            practical_meaning=practical,
            life_translation=life_translation,
            guidance=guidance,
            prompt=prompt,
            timing_focus=prediction_cards[0].summary if prediction_cards else None,
            ritual_focus=ritual_focus,
            oracle=oracle,
        )
