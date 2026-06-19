from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.models.chart import (
    BirthProfile,
    DailyHoroscope,
    InterpretationBlock,
    NatalTechnicalChart,
    PredictionCard,
    TopicJudgmentRecord,
    TransitAspectRecord,
    YearMapRecord,
)
from app.services.aspect_service import AspectPolicyService
from app.services.astrology_settings import MAJOR_PLANETS
from app.services.chart_engine import NatalChartEngine
from app.services.citation_service import CitationService


class TransitForecastService:
    TRANSIT_PLANET_WEIGHTS = {
        "Moon": 7,
        "Sun": 6,
        "Mercury": 5,
        "Venus": 5,
        "Mars": 5,
        "Jupiter": 4,
        "Saturn": 4,
    }
    NATAL_TARGET_WEIGHTS = {
        "Asc": 8,
        "Sun": 7,
        "Moon": 7,
        "Venus": 6,
        "Mars": 6,
        "Saturn": 5,
        "Mercury": 5,
        "Jupiter": 4,
        "MC": 4,
    }
    PEAK_WINDOW_DAYS = {
        "Moon": 0.33,
        "Sun": 0.75,
        "Mercury": 1.0,
        "Venus": 1.0,
        "Mars": 2.0,
        "Jupiter": 4.0,
        "Saturn": 7.0,
    }
    SAMPLE_STEP_HOURS = {
        "Moon": 1,
        "Sun": 3,
        "Mercury": 4,
        "Venus": 4,
        "Mars": 8,
        "Jupiter": 12,
        "Saturn": 12,
    }
    SEARCH_CAP_DAYS = {
        "Moon": 2.0,
        "Sun": 14.0,
        "Mercury": 21.0,
        "Venus": 21.0,
        "Mars": 45.0,
        "Jupiter": 120.0,
        "Saturn": 180.0,
    }
    HOUSE_LIVED_TOPICS = {
        1: ["body", "appearance", "identity", "temperament", "visibility", "confidence", "first impressions"],
        2: ["money", "income", "possessions", "self-worth", "security", "skills", "what you can sustain"],
        3: ["speech", "writing", "siblings", "neighbors", "short trips", "learning", "daily coordination"],
        4: ["home", "family", "ancestry", "private life", "property", "roots", "emotional foundation"],
        5: ["children", "pleasure", "romance", "creativity", "play", "performance", "risk", "joy"],
        6: ["workload", "health routines", "service", "coworkers", "maintenance", "habits", "obligations"],
        7: ["partnership", "marriage", "contracts", "clients", "opponents", "cooperation", "mirroring"],
        8: ["shared money", "debt", "taxes", "inheritance", "intimacy", "fear", "loss", "psychological release"],
        9: ["belief", "education", "travel", "law", "publishing", "mentors", "meaning", "worldview"],
        10: ["career", "reputation", "authority", "leadership", "public life", "ambition", "visible duty"],
        11: ["friends", "patrons", "networks", "allies", "audience", "long-term hopes", "community support"],
        12: ["rest", "retreat", "hidden pressure", "grief", "solitude", "sacrifice", "private healing"],
    }
    HOUSE_PLAIN_MEANINGS = {
        1: "The First House speaks through the body, identity, appearance, confidence, and how people first meet you.",
        2: "The Second House speaks through money, possessions, self-worth, and what helps you feel materially steady.",
        3: "The Third House speaks through speech, errands, writing, siblings, neighbors, and the rhythm of daily coordination.",
        4: "The Fourth House speaks through home, family, ancestry, private life, property, and your emotional base.",
        5: "The Fifth House speaks through children, romance, creativity, pleasure, performance, play, and risk.",
        6: "The Sixth House speaks through work routines, stress, maintenance, service, and the tasks that keep life running.",
        7: "The Seventh House speaks through partners, clients, contracts, conflict, and the people who mirror you back to yourself.",
        8: "The Eighth House speaks through shared money, debt, taxes, fear, vulnerability, intimacy, grief, and deep emotional release.",
        9: "The Ninth House speaks through belief, study, travel, law, publishing, and the search for meaning.",
        10: "The Tenth House speaks through career, authority, reputation, responsibility, and public visibility.",
        11: "The Eleventh House speaks through friends, allies, networks, patrons, audience, and long-range hopes.",
        12: "The Twelfth House speaks through retreat, exhaustion, hidden pressure, grief, solitude, and what must be processed privately.",
    }
    PLANET_PLAIN_MEANINGS = {
        "Sun": "identity, purpose, vitality, and visibility",
        "Moon": "emotions, habits, embodiment, and felt security",
        "Mercury": "thinking, speech, logistics, and decision-making",
        "Venus": "love, attraction, pleasure, harmony, and value",
        "Mars": "drive, anger, pressure, courage, and conflict",
        "Jupiter": "growth, relief, generosity, belief, and opportunity",
        "Saturn": "duty, fear, structure, restraint, and long-term reality",
        "Asc": "the body, appearance, style, and first impression",
        "MC": "career, direction, reputation, and public standing",
    }
    ASPECT_PLAIN_MEANINGS = {
        "Conjunction": "merges the two themes and makes them impossible to ignore",
        "Sextile": "opens a useful door, but still asks for a deliberate response",
        "Square": "creates friction, pressure, and a need to adjust",
        "Trine": "supports flow, ease, and natural expression",
        "Opposition": "brings a revealing tension that asks for balance or perspective",
    }

    @staticmethod
    def _resolve_labels(citation_ids: List[str]) -> List[str]:
        resolved = CitationService.resolve(citation_ids)
        return [item.get("label", item.get("id", "")) for item in resolved]

    @staticmethod
    def _planet_rite_lookup(ontology: Dict) -> Dict[str, Dict]:
        return {item["planet"]: item for item in ontology.get("planetary_rites", [])}

    @staticmethod
    def _threshold_lookup(ontology: Dict) -> Dict[str, Dict]:
        return {item["aspect"]: item for item in ontology.get("transit_thresholds", [])}

    @staticmethod
    def _find_planet(chart_data: NatalTechnicalChart, name: str):
        return next((planet for planet in chart_data.planets if planet.id == name), None)

    @staticmethod
    def _find_angle(chart_data: NatalTechnicalChart, name: str):
        return next((angle for angle in chart_data.angles if angle.id == name), None)

    @staticmethod
    def _display_body_name(name: str) -> str:
        return {
            "Asc": "rising sign",
            "MC": "midheaven",
        }.get(name, name)

    @staticmethod
    def _format_offset(dt: datetime) -> str:
        offset = dt.utcoffset() or timedelta(0)
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        total_minutes = abs(total_minutes)
        hours, minutes = divmod(total_minutes, 60)
        return f"{sign}{hours:02d}:{minutes:02d}"

    @classmethod
    def _current_local_dt(cls, profile: BirthProfile, resolved_timezone: Optional[str] = None) -> Tuple[datetime, str]:
        timezone_name = profile.current_timezone_name or resolved_timezone or profile.timezone_name
        if timezone_name:
            local_dt = datetime.now(ZoneInfo(timezone_name))
            return local_dt, timezone_name
        if profile.current_utc_offset:
            sign = 1 if profile.current_utc_offset.startswith("+") else -1
            hours, minutes = profile.current_utc_offset[1:].split(":")
            tz = timezone(sign * timedelta(hours=int(hours), minutes=int(minutes)))
            return datetime.now(tz), profile.current_utc_offset
        if profile.utc_offset:
            sign = 1 if profile.utc_offset.startswith("+") else -1
            hours, minutes = profile.utc_offset[1:].split(":")
            tz = timezone(sign * timedelta(hours=int(hours), minutes=int(minutes)))
            return datetime.now(tz), profile.utc_offset
        return datetime.now(timezone.utc), "UTC"

    @classmethod
    def _current_coordinates(cls, profile: BirthProfile) -> Tuple[float, float, str]:
        if profile.current_latitude is not None and profile.current_longitude is not None:
            return profile.current_latitude, profile.current_longitude, "current_location"
        if profile.latitude is not None and profile.longitude is not None:
            return profile.latitude, profile.longitude, "birth_location_fallback"
        return 0.0, 0.0, "missing_location"

    @classmethod
    def calculate_current_transit_chart(
        cls,
        profile: BirthProfile,
        resolved_timezone: Optional[str] = None,
    ) -> Tuple[NatalTechnicalChart, str, str, str]:
        local_dt, timezone_label = cls._current_local_dt(profile, resolved_timezone)
        transit_chart = cls.calculate_transit_chart_for_dt(profile, local_dt)
        _, _, location_status = cls._current_coordinates(profile)
        return transit_chart, local_dt.isoformat(), timezone_label, location_status

    @classmethod
    def calculate_transit_chart_for_dt(cls, profile: BirthProfile, dt: datetime) -> NatalTechnicalChart:
        latitude, longitude, _ = cls._current_coordinates(profile)
        return NatalChartEngine.calculate_chart(
            date_text=dt.strftime("%Y-%m-%d"),
            time_text=dt.strftime("%H:%M"),
            utc_offset=cls._format_offset(dt),
            latitude=latitude,
            longitude=longitude,
        )

    @staticmethod
    def _normalized_chart_cache_key(dt: datetime) -> str:
        return dt.replace(second=0, microsecond=0).isoformat()

    @staticmethod
    def _angular_difference(first: float, second: float) -> float:
        return AspectPolicyService.angular_difference(first, second)

    @classmethod
    def _contact_priority(cls, contact: TransitAspectRecord) -> Tuple[float, float, float]:
        transit_weight = cls.TRANSIT_PLANET_WEIGHTS.get(contact.transit_body, 1)
        natal_weight = cls.NATAL_TARGET_WEIGHTS.get(contact.natal_body, 1)
        aspect_weight = {"Conjunction": 5, "Opposition": 4, "Square": 4, "Trine": 3, "Sextile": 2}.get(contact.type, 1)
        return (-(transit_weight + natal_weight + aspect_weight), contact.orb, contact.transit_body < contact.natal_body)

    @classmethod
    def _parse_timestamp(cls, transit_timestamp: Optional[str]) -> Optional[datetime]:
        if not transit_timestamp:
            return None
        try:
            return datetime.fromisoformat(transit_timestamp)
        except ValueError:
            return None

    @staticmethod
    def _signed_longitude_delta(current: float, target: float) -> float:
        return ((target - current + 540.0) % 360.0) - 180.0

    @classmethod
    def _nearest_exact_longitude(cls, transit_longitude: float, target_longitude: float, aspect_degrees: int) -> float:
        candidates = [
            (target_longitude + aspect_degrees) % 360.0,
            (target_longitude - aspect_degrees) % 360.0,
        ]
        return min(candidates, key=lambda candidate: abs(cls._signed_longitude_delta(transit_longitude, candidate)))

    @classmethod
    def _sample_step_hours(cls, transit_body: str) -> int:
        return cls.SAMPLE_STEP_HOURS.get(transit_body, 6)

    @classmethod
    def _search_cap_days(cls, transit_body: str) -> float:
        return cls.SEARCH_CAP_DAYS.get(transit_body, 30.0)

    @classmethod
    def _transit_planet_at(
        cls,
        profile: BirthProfile,
        dt: datetime,
        transit_body: str,
        chart_cache: Dict[str, NatalTechnicalChart],
    ):
        cache_key = cls._normalized_chart_cache_key(dt)
        chart = chart_cache.get(cache_key)
        if chart is None:
            chart = cls.calculate_transit_chart_for_dt(profile, dt)
            chart_cache[cache_key] = chart
        return cls._find_planet(chart, transit_body)

    @classmethod
    def _exact_delta_at(
        cls,
        profile: BirthProfile,
        dt: datetime,
        transit_body: str,
        exact_longitude: float,
        chart_cache: Dict[str, NatalTechnicalChart],
    ) -> Optional[float]:
        planet = cls._transit_planet_at(profile, dt, transit_body, chart_cache)
        if not planet:
            return None
        return cls._signed_longitude_delta(planet.longitude, exact_longitude)

    @classmethod
    def _estimate_timing(
        cls,
        profile: BirthProfile,
        transit_body: str,
        transit_longitude: float,
        transit_speed: Optional[float],
        target_longitude: float,
        aspect_degrees: int,
        current_orb: float,
        transit_timestamp: Optional[str],
        chart_cache: Dict[str, NatalTechnicalChart],
    ) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        reference_dt = cls._parse_timestamp(transit_timestamp)
        if transit_speed is None or abs(transit_speed) < 0.0001:
            return "steady", None, None, None

        exact_longitude = cls._nearest_exact_longitude(transit_longitude, target_longitude, aspect_degrees)
        delta_now = cls._signed_longitude_delta(transit_longitude, exact_longitude)
        estimated_days = delta_now / transit_speed
        estimated_exact_dt = reference_dt + timedelta(days=estimated_days) if reference_dt else None

        if reference_dt is None:
            if current_orb <= 0.05:
                return "exact", None, None, None
            return ("applying" if estimated_days >= 0 else "separating"), None, None, None

        exact_dt = estimated_exact_dt or reference_dt
        search_cap = cls._search_cap_days(transit_body)
        bounded_days = max(min(estimated_days, search_cap), -search_cap)
        exact_dt = reference_dt + timedelta(days=bounded_days)
        step_hours = cls._sample_step_hours(transit_body)
        window_days = min(max(abs(bounded_days) * 0.6, step_hours / 24.0), search_cap)
        start_dt = exact_dt - timedelta(days=window_days)
        end_dt = exact_dt + timedelta(days=window_days)

        samples: List[Tuple[datetime, float]] = []
        cursor = start_dt
        while cursor <= end_dt:
            delta = cls._exact_delta_at(profile, cursor, transit_body, exact_longitude, chart_cache)
            if delta is not None:
                samples.append((cursor, delta))
            cursor += timedelta(hours=step_hours)
        if not any(sample_dt == reference_dt for sample_dt, _ in samples):
            delta = cls._exact_delta_at(profile, reference_dt, transit_body, exact_longitude, chart_cache)
            if delta is not None:
                samples.append((reference_dt, delta))

        samples.sort(key=lambda item: item[0])
        best_dt = exact_dt
        best_delta = delta_now
        if samples:
            best_dt, best_delta = min(samples, key=lambda item: abs(item[1]))

        bracket: Optional[Tuple[datetime, float, datetime, float]] = None
        for (left_dt, left_delta), (right_dt, right_delta) in zip(samples, samples[1:]):
            if left_delta == 0:
                best_dt, best_delta = left_dt, left_delta
                bracket = None
                break
            if right_delta == 0:
                best_dt, best_delta = right_dt, right_delta
                bracket = None
                break
            if left_delta * right_delta < 0:
                bracket = (left_dt, left_delta, right_dt, right_delta)
                break

        if bracket is not None:
            left_dt, left_delta, right_dt, right_delta = bracket
            for _ in range(12):
                midpoint = left_dt + (right_dt - left_dt) / 2
                mid_delta = cls._exact_delta_at(profile, midpoint, transit_body, exact_longitude, chart_cache)
                if mid_delta is None:
                    break
                best_dt, best_delta = midpoint, mid_delta
                if abs(mid_delta) <= 0.005:
                    break
                if left_delta * mid_delta <= 0:
                    right_dt, right_delta = midpoint, mid_delta
                else:
                    left_dt, left_delta = midpoint, mid_delta
            exact_dt = best_dt
        else:
            exact_dt = best_dt

        if abs(delta_now) <= 0.05 or abs(exact_dt - reference_dt) <= timedelta(hours=max(step_hours / 2, 1)):
            phase = "exact"
        elif exact_dt > reference_dt:
            phase = "applying"
        elif exact_dt < reference_dt:
            phase = "separating"
        else:
            phase = "steady"

        window_days = cls.PEAK_WINDOW_DAYS.get(transit_body, 1.0)
        window_start = exact_dt - timedelta(days=window_days)
        window_end = exact_dt + timedelta(days=window_days)
        return phase, exact_dt.isoformat(), window_start.isoformat(), window_end.isoformat()

    @classmethod
    def build_transit_contacts(
        cls,
        profile: BirthProfile,
        transit_chart: NatalTechnicalChart,
        natal_chart: NatalTechnicalChart,
        natal_owner: str = "self",
        limit: int = 8,
        transit_timestamp: Optional[str] = None,
    ) -> List[TransitAspectRecord]:
        targets = [
            {
                "id": planet.id,
                "sign": planet.sign,
                "longitude": planet.longitude,
                "house": planet.house,
            }
            for planet in natal_chart.planets
        ]
        for angle_name in ["Asc", "MC"]:
            angle = cls._find_angle(natal_chart, angle_name)
            if angle:
                targets.append(
                    {
                        "id": angle.id,
                        "sign": angle.sign,
                        "longitude": angle.longitude,
                        "house": None,
                    }
                )

        contacts: List[TransitAspectRecord] = []
        chart_cache: Dict[str, NatalTechnicalChart] = {}
        for transit_planet in transit_chart.planets:
            if transit_planet.id not in MAJOR_PLANETS:
                continue
            for target in targets:
                aspect = AspectPolicyService.detect_aspect(
                    first_body=transit_planet.id,
                    first_longitude=transit_planet.longitude,
                    second_body=target["id"],
                    second_longitude=target["longitude"],
                    context="transit",
                )
                if aspect:
                    phase, exact_at, peak_window_start, peak_window_end = cls._estimate_timing(
                        profile=profile,
                        transit_body=transit_planet.id,
                        transit_longitude=transit_planet.longitude,
                        transit_speed=transit_planet.longitude_speed,
                        target_longitude=target["longitude"],
                        aspect_degrees=aspect.degrees,
                        current_orb=aspect.orb,
                        transit_timestamp=transit_timestamp,
                        chart_cache=chart_cache,
                    )
                    contacts.append(
                        TransitAspectRecord(
                            transit_body=transit_planet.id,
                            transit_sign=transit_planet.sign,
                            transit_house=transit_planet.house,
                            natal_owner=natal_owner,
                            natal_body=target["id"],
                            natal_sign=target["sign"],
                            natal_house=target["house"],
                            type=aspect.type,
                            degrees=aspect.degrees,
                            orb=aspect.orb,
                            phase=phase,
                            exact_at=exact_at,
                            peak_window_start=peak_window_start,
                            peak_window_end=peak_window_end,
                        )
                    )

        deduped: List[TransitAspectRecord] = []
        seen = set()
        for contact in sorted(contacts, key=cls._contact_priority):
            key = (contact.transit_body, contact.natal_owner, contact.natal_body, contact.type)
            if key in seen:
                continue
            deduped.append(contact)
            seen.add(key)
        return deduped[:limit]

    @classmethod
    def _contact_narrative(cls, contact: TransitAspectRecord, ontology: Dict) -> str:
        rites = cls._planet_rite_lookup(ontology)
        thresholds = cls._threshold_lookup(ontology)
        transit_meta = rites.get(contact.transit_body, {})
        natal_meta = rites.get(contact.natal_body, {})
        threshold_meta = thresholds.get(contact.type, {})
        omens = threshold_meta.get("omens", []) or transit_meta.get("omens", [])
        omen_phrase = ", ".join(omens[:3]) if omens else "meaningful pressure"
        return (
            f"Transit {contact.transit_body} in {contact.transit_sign} {contact.type.lower()} natal {contact.natal_body} in {contact.natal_sign} "
            f"tightens the field around {omen_phrase}. {threshold_meta.get('action', 'Answer the contact with a conscious act.')}"
        )

    @classmethod
    def build_natal_transit_block(
        cls,
        contacts: List[TransitAspectRecord],
        transit_timestamp: str,
        transit_timezone: str,
        ontology: Dict,
    ) -> Optional[InterpretationBlock]:
        if not contacts:
            return None
        top_contact = contacts[0]
        threshold_meta = cls._threshold_lookup(ontology).get(top_contact.type, {})
        return InterpretationBlock(
            block_type="transit_current",
            title=f"What is active in your chart right now: {top_contact.transit_body} and {cls._display_body_name(top_contact.natal_body)}",
            summary=(
                f"As of {transit_timestamp[:16].replace('T', ' ')} {transit_timezone}, the live field is led by "
                f"{cls._contact_narrative(top_contact, ontology)} {threshold_meta.get('levi_frame', '')}"
            ).strip(),
            citations=cls._resolve_labels([
                *threshold_meta.get("source_lens_tags", []),
                *cls._planet_rite_lookup(ontology).get(top_contact.transit_body, {}).get("source_lens_tags", []),
            ]),
        )

    @classmethod
    def build_synastry_transit_block(
        cls,
        contacts: List[TransitAspectRecord],
        transit_timestamp: str,
        transit_timezone: str,
        ontology: Dict,
    ) -> Optional[InterpretationBlock]:
        if not contacts:
            return None
        top_contact = contacts[0]
        threshold_meta = cls._threshold_lookup(ontology).get(top_contact.type, {})
        owner_label = top_contact.natal_owner.capitalize()
        return InterpretationBlock(
            block_type="transit_current",
            title=f"What is active for {owner_label} right now: {top_contact.transit_body} and {cls._display_body_name(top_contact.natal_body)}",
            summary=(
                f"As of {transit_timestamp[:16].replace('T', ' ')} {transit_timezone}, the shared field is led by "
                f"{top_contact.transit_body} {top_contact.type.lower()} {top_contact.natal_owner}'s natal {top_contact.natal_body}. "
                f"{threshold_meta.get('levi_frame', '')}"
            ).strip(),
            citations=cls._resolve_labels([
                *threshold_meta.get("source_lens_tags", []),
                *cls._planet_rite_lookup(ontology).get(top_contact.transit_body, {}).get("source_lens_tags", []),
            ]),
        )

    @staticmethod
    def _house_lookup(ontology: Dict) -> Dict[int, Dict]:
        return {item["house_number"]: item for item in ontology.get("houses", [])}

    @staticmethod
    def _topic_phrase(values: List[str], limit: int = 3) -> str:
        items = [value for value in values[:limit] if value]
        if not items:
            return "the active topics of the day"
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return ", ".join(items[:-1]) + f", and {items[-1]}"

    @classmethod
    def _house_meta_from_id(cls, ontology: Dict, house_id: Optional[str]) -> Dict:
        if not house_id or not house_id.startswith("House"):
            return {}
        try:
            house_number = int(house_id.replace("House", ""))
        except ValueError:
            return {}
        return cls._house_lookup(ontology).get(house_number, {})

    @classmethod
    def _house_title(cls, ontology: Dict, house_id: Optional[str]) -> str:
        house_meta = cls._house_meta_from_id(ontology, house_id)
        return house_meta.get("display_name", house_id or "the relevant part of life")

    @classmethod
    def _house_topics(cls, ontology: Dict, house_id: Optional[str]) -> str:
        house_meta = cls._house_meta_from_id(ontology, house_id)
        topics = house_meta.get("classical_topics", []) or house_meta.get("modern_topics", [])
        return cls._topic_phrase(topics, 3)

    @staticmethod
    def _body_theme(name: str) -> str:
        return TransitForecastService.PLANET_PLAIN_MEANINGS.get(name, f"{name.lower()} matters")

    @staticmethod
    def _house_number(house_id: Optional[str]) -> Optional[int]:
        if not house_id or not house_id.startswith("House"):
            return None
        try:
            return int(house_id.replace("House", ""))
        except ValueError:
            return None

    @classmethod
    def _house_lived_topics(cls, ontology: Dict, house_id: Optional[str]) -> List[str]:
        house_number = cls._house_number(house_id)
        if house_number in cls.HOUSE_LIVED_TOPICS:
            return cls.HOUSE_LIVED_TOPICS[house_number]
        house_meta = cls._house_meta_from_id(ontology, house_id)
        return house_meta.get("classical_topics", []) or house_meta.get("modern_topics", []) or ["the active part of life"]

    @classmethod
    def _house_plain_meaning(cls, ontology: Dict, house_id: Optional[str]) -> str:
        house_number = cls._house_number(house_id)
        if house_number in cls.HOUSE_PLAIN_MEANINGS:
            return cls.HOUSE_PLAIN_MEANINGS[house_number]
        title = cls._house_title(ontology, house_id)
        topics = cls._topic_phrase(cls._house_lived_topics(ontology, house_id), 4)
        return f"{title} speaks through {topics}."

    @staticmethod
    def _aspect_plain_meaning(aspect_type: str) -> str:
        return TransitForecastService.ASPECT_PLAIN_MEANINGS.get(aspect_type, "pulls the themes into noticeable contact")

    @classmethod
    def _main_transit_summary(cls, contact: TransitAspectRecord) -> str:
        return (
            f"Today's leading signature is {contact.transit_body} {contact.type.lower()} "
            f"your {cls._display_body_name(contact.natal_body)}: "
            f"{cls._body_theme(contact.transit_body)} meets {cls._body_theme(contact.natal_body)}."
        )

    @staticmethod
    def _orb_intensity(orb: float) -> str:
        if orb <= 0.5:
            return "very strong and immediate"
        if orb <= 1.5:
            return "strong and hard to miss"
        if orb <= 3.0:
            return "moderately strong"
        return "present, but more atmospheric than overwhelming"

    @classmethod
    def _phase_and_orb_sentence(cls, contact: TransitAspectRecord) -> str:
        intensity = cls._orb_intensity(contact.orb)
        if contact.phase == "applying":
            return (
                f"This transit is applying at {contact.orb:.1f}°, so it is still building. "
                f"The influence is {intensity}, and today is best used to prepare, respond early, or make the first adjustment before the peak."
            )
        if contact.phase == "separating":
            return (
                f"This transit is separating at {contact.orb:.1f}°, so the peak has just passed. "
                f"The influence is still {intensity}, but the task now is integration rather than escalation."
            )
        if contact.phase == "exact":
            return (
                f"This transit is exact at {contact.orb:.1f}°, so the theme is at full volume. "
                f"The influence is {intensity}, and the day is better used consciously than left to mood or chance."
            )
        return (
            f"The orb is {contact.orb:.1f}°, which makes this influence {intensity}. "
            "Even if the timing is less dramatic, it is still active enough to deserve a deliberate response."
        )

    @staticmethod
    def _nonfatalistic(text: str) -> str:
        return (
            text.replace(" will ", " may ")
            .replace(" will.", " may.")
            .replace(" must ", " can ")
            .replace(" guarantees ", " can support ")
            .replace(" guarantee ", " support ")
        )

    @classmethod
    def _natal_condition_line(cls, chart_data: Optional[NatalTechnicalChart], natal_body: str) -> Optional[str]:
        if not chart_data:
            return None
        planet = cls._find_planet(chart_data, natal_body)
        if not planet:
            return None
        condition_bits = [
            planet.house_condition,
            planet.traditional_strength,
            "retrograde" if planet.retrograde else None,
        ]
        condition_bits = [bit.replace("_", " ") for bit in condition_bits if bit]
        if not condition_bits:
            return None
        return (
            f"Your natal {natal_body} is carrying a {', '.join(condition_bits)} condition, "
            "so this transit is touching a part of the chart that already has its own temperament and history."
        )

    @classmethod
    def _fortune_spirit_line(cls, chart_data: Optional[NatalTechnicalChart]) -> Optional[str]:
        if not chart_data or not chart_data.traditional_context:
            return None
        fortune = chart_data.traditional_context.fortune
        spirit = chart_data.traditional_context.spirit
        if not fortune and not spirit:
            return None
        pieces: List[str] = []
        if fortune:
            pieces.append(
                f"Fortune in {(fortune.house or 'the relevant house').replace('House', 'House ')} points toward circumstances, material realities, and what life places in your hands through {cls._topic_phrase(cls._house_lived_topics({}, fortune.house), 4)}"
            )
        if spirit:
            pieces.append(
                f"Spirit in {(spirit.house or 'the relevant house').replace('House', 'House ')} points toward chosen direction, intention, and what you try to shape through {cls._topic_phrase(cls._house_lived_topics({}, spirit.house), 4)}"
            )
        return ". ".join(pieces) + "."

    @classmethod
    def _annual_story_line(
        cls,
        year_map: Optional[YearMapRecord],
        chart_data: Optional[NatalTechnicalChart],
        house_title: str,
    ) -> str:
        if not year_map:
            return (
                f"Even without a louder annual trigger, today's transit still concentrates attention in {house_title.lower()}, "
                "so the daily weather is telling you where life is asking for presence right now."
            )
        activated_topics = cls._topic_phrase(year_map.activated_topics, 5) if year_map.activated_topics else house_title.lower()
        lord_bits = []
        if year_map.lord_of_year:
            lord_bits.append(f"the lord of the year is {year_map.lord_of_year}")
        if year_map.lord_of_year_house:
            lord_bits.append(f"natal {year_map.lord_of_year} is acting from the natal {year_map.lord_of_year_house.replace('House', 'House ')}")
        if year_map.lord_of_year_condition:
            lord_bits.append(f"its condition is {year_map.lord_of_year_condition.replace('_', ' ')}")
        lord_line = f" In practical terms, {'; '.join(lord_bits)}." if lord_bits else ""
        fortune_line = ""
        if year_map.fortune_emphasis:
            fortune_line = f" {year_map.fortune_emphasis}"
        if year_map.spirit_emphasis:
            fortune_line += f" {year_map.spirit_emphasis}"
        return (
            f"Your annual profection keeps returning you to {activated_topics}. "
            f"That means today's event is not random; it is touching the same yearly storyline from the angle of {house_title.lower()}.{lord_line}{fortune_line}"
        ).strip()

    @classmethod
    def _overlay_line(cls, threshold_meta: Dict, rite_meta: Dict) -> Optional[str]:
        overlays = [threshold_meta.get("levi_frame"), rite_meta.get("jung_frame")]
        overlays = [item.strip() for item in overlays if item and item.strip()]
        if not overlays:
            return None
        return (
            f"Symbolically, {overlays[0]} In lived terms, treat that image as a prompt to become more conscious, not as a fate statement."
        )

    @classmethod
    def _opportunity_lines(cls, house_number: Optional[int], house_title: str, transit_body: str, natal_body: str) -> List[str]:
        base = {
            1: [
                "Dress or present yourself with more intention before an important interaction.",
                "Make one visible move that reminds other people who you are and what you stand for.",
                "Adjust your schedule so your body is not carrying avoidable stress all day.",
            ],
            4: [
                "Handle one home, family, or property task that has been quietly draining your attention.",
                "Create a calmer private environment before you tackle public demands.",
                "Have one honest conversation about what is happening in the family or household.",
            ],
            5: [
                "Turn a creative idea into one scheduled action instead of leaving it as a mood.",
                "Use warmth to reconnect with a child, lover, audience, or pleasure practice.",
                "Choose joy that restores you rather than stimulation that scatters you.",
            ],
            8: [
                "Handle one shared-money issue directly instead of letting fear enlarge it in the background.",
                "Name one private fear out loud so it stops governing the day from the shadows.",
                "Let one trusted conversation become more honest about intimacy, dependence, or trust.",
            ],
            11: [
                "Reach out to one friend, ally, patron, or audience member with a clear purpose.",
                "Ask for support in a way that gives other people something concrete to answer.",
                "Reconnect today's effort to a long-term hope so the day serves a bigger future.",
            ],
        }.get(house_number, [])
        generic = [
            f"Make one concrete decision in {house_title.lower()} instead of leaving the issue at the level of feeling.",
            f"Use {transit_body.lower()} energy to respond more consciously around {cls._body_theme(natal_body)}.",
        ]
        return (base + generic)[:4]

    @classmethod
    def _watch_for_lines(cls, house_number: Optional[int], transit_body: str, aspect_type: str) -> List[str]:
        base = {
            1: [
                "Do not let one moment of self-consciousness define the whole day.",
                "Avoid reshaping your presentation only to win quick approval.",
            ],
            4: [
                "Do not drag private stress into every public decision.",
                "Avoid assuming that comfort and withdrawal are the same thing.",
            ],
            5: [
                "Do not confuse temporary attention with lasting affection or security.",
                "Avoid overspending, overpromising, or overperforming just to lift your mood.",
            ],
            8: [
                "Do not let anxiety about money, trust, or intimacy become silent control.",
                "Avoid catastrophizing shared obligations before you have actual facts.",
            ],
            11: [
                "Do not mistake online attention or group approval for real support.",
                "Avoid saying yes to every invitation if it pulls you away from the larger goal.",
            ],
        }.get(house_number, [])
        generic = [
            f"Watch for the shadow side of {transit_body.lower()}: excess, haste, defensiveness, or drift.",
            f"Because this is a {aspect_type.lower()}, do not let pressure turn into a story that everything is wrong.",
        ]
        return (base + generic)[:4]

    @classmethod
    def _checklist_lines(cls, primary: str, supporting: List[str], cautions: List[str]) -> List[str]:
        checklist = [primary, *supporting[:2]]
        if cautions:
            checklist.append(cautions[0].replace("Do not ", "Avoid ").replace("Watch for ", "Notice and redirect "))
        return [item.rstrip(".") + "." for item in checklist[:5]]

    @classmethod
    def _score_section(cls, text: str, required_terms: List[str]) -> int:
        score = 3
        lowered = text.lower()
        if len(text.split()) >= 18:
            score += 1
        if any(term in lowered for term in required_terms):
            score += 1
        return min(score, 5)

    @classmethod
    def _score_daily_horoscope(cls, payload: Dict) -> Dict[str, int]:
        joined_what = " ".join(payload.get("what_this_means", []))
        joined_why = " ".join(payload.get("why_the_chart_says_this", []))
        joined_actions = " ".join(payload.get("opportunities", []) + payload.get("watch_fors", []) + payload.get("action_checklist", []))
        combined = " ".join([
            payload.get("headline", ""),
            payload.get("main_transit", ""),
            payload.get("day_thesis", ""),
            joined_what,
            joined_why,
            payload.get("larger_story", ""),
            payload.get("timing", ""),
            joined_actions,
        ]).lower()
        action_terms = ["make", "ask", "handle", "schedule", "clean", "say", "write", "review", "avoid", "reach out", "talk"]
        scores = {
            "clarity": cls._score_section(joined_what + " " + payload.get("day_thesis", ""), ["because", "means", "today"]),
            "specificity": cls._score_section(joined_actions + " " + payload.get("timing", ""), ["house", "orb", "today", "money", "home", "relationship"]),
            "practical_usefulness": 5 if sum(1 for term in action_terms if term in joined_actions.lower()) >= 3 else 3,
            "astrological_explanation": cls._score_section(joined_why + " " + payload.get("main_transit", ""), ["house", "jupiter", "saturn", "venus", "mars", "moon", "sun", "orb", "applying", "separating"]),
            "emotional_resonance": cls._score_section(joined_what, ["feel", "pressure", "fear", "confidence", "warmth", "emotion", "sensitive"]),
            "non_fatalistic_language": 5 if all(token not in combined for token in [" guaranteed", " destiny", " fated", " unavoidable"]) and any(token in combined for token in [" may ", " can ", " watch for "]) else 3,
        }
        return scores

    @classmethod
    def _revise_daily_horoscope(cls, payload: Dict, scores: Dict[str, int], house_plain_meaning: str, contact: TransitAspectRecord) -> Dict:
        if scores["clarity"] < 4:
            payload["day_thesis"] = cls._nonfatalistic(
                f"Today is about responding consciously to {cls._display_body_name(contact.natal_body).lower()} matters instead of letting mood, pressure, or praise run the day."
            )
        if scores["specificity"] < 4:
            payload["opportunities"] = payload.get("opportunities", []) + [
                f"Pick one specific conversation, payment, creative step, or boundary that can be finished before the day ends."
            ]
        if scores["practical_usefulness"] < 4:
            payload["best_move_primary"] = payload.get("best_move_primary") or "Handle the one issue today that has the clearest real-world consequence."
            payload["best_move_supporting"] = (payload.get("best_move_supporting", []) + [
                "Write down the exact next step before the day gets noisy.",
                "Choose one action that helps future-you, not just current mood.",
            ])[:3]
        if scores["astrological_explanation"] < 4:
            payload["why_the_chart_says_this"] = payload.get("why_the_chart_says_this", []) + [house_plain_meaning]
        if scores["emotional_resonance"] < 4:
            payload["what_this_means"] = payload.get("what_this_means", []) + [
                "Emotionally, this can feel bigger than the outer event, so name what you are actually feeling before you react."
            ]
        if scores["non_fatalistic_language"] < 4:
            for key in ["headline", "main_transit", "day_thesis", "larger_story", "timing"]:
                if payload.get(key):
                    payload[key] = cls._nonfatalistic(payload[key])
            payload["what_this_means"] = [cls._nonfatalistic(item) for item in payload.get("what_this_means", [])]
            payload["why_the_chart_says_this"] = [cls._nonfatalistic(item) for item in payload.get("why_the_chart_says_this", [])]
        payload["action_checklist"] = cls._checklist_lines(
            payload.get("best_move_primary") or "Choose one clear action.",
            payload.get("best_move_supporting", []),
            payload.get("watch_fors", []),
        )
        return payload

    @classmethod
    def _format_calendar_label(cls, timestamp: Optional[str]) -> str:
        parsed = cls._parse_timestamp(timestamp)
        if not parsed:
            return "today"
        return parsed.strftime("%A, %B %d, %Y").replace(" 0", " ")

    @classmethod
    def _format_moment_label(cls, timestamp: Optional[str], timezone_label: Optional[str] = None) -> Optional[str]:
        parsed = cls._parse_timestamp(timestamp)
        if not parsed:
            return None
        stamp = parsed.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")
        return f"{stamp} {timezone_label}".strip() if timezone_label else stamp

    @classmethod
    def _timing_sentence(cls, contact: TransitAspectRecord, transit_timezone: str) -> str:
        exact_label = cls._format_moment_label(contact.exact_at, transit_timezone)
        window_start = cls._format_moment_label(contact.peak_window_start, transit_timezone)
        window_end = cls._format_moment_label(contact.peak_window_end, transit_timezone)
        if contact.phase == "exact" and exact_label:
            return f"This contact is exact now, with its clearest expression around {exact_label}."
        if contact.phase == "applying" and exact_label:
            return f"This influence is still building and points toward an exact hit around {exact_label}."
        if contact.phase == "separating" and exact_label:
            return f"This influence has just passed its exact point near {exact_label}, but it is still echoing through the day."
        if window_start and window_end:
            return f"Its strongest window runs from {window_start} through {window_end}."
        return "This influence is live today, so respond to it in real time instead of reading it only in retrospect."

    @classmethod
    def _transit_line(cls, contact: TransitAspectRecord, ontology: Dict) -> str:
        natal_house = cls._house_title(ontology, contact.natal_house)
        lived_topics = cls._topic_phrase(cls._house_lived_topics(ontology, contact.natal_house or contact.transit_house), 4)
        phase_bits = [contact.phase or None, f"orb {contact.orb:.1f}°"]
        return (
            f"{contact.transit_body} {contact.type.lower()} {cls._display_body_name(contact.natal_body)}"
            f" in {natal_house.lower()} — {lived_topics} ({' • '.join(bit for bit in phase_bits if bit)})"
        )

    @classmethod
    def build_natal_daily_horoscope(
        cls,
        contacts: List[TransitAspectRecord],
        transit_timestamp: Optional[str],
        transit_timezone: Optional[str],
        ontology: Dict,
        year_map: Optional[YearMapRecord] = None,
        topic_judgments: Optional[List[TopicJudgmentRecord]] = None,
        chart_data: Optional[NatalTechnicalChart] = None,
    ) -> Optional[DailyHoroscope]:
        topic_judgments = topic_judgments or []
        transit_timezone = transit_timezone or "local time"
        top_contact = contacts[0] if contacts else None
        second_contact = contacts[1] if len(contacts) > 1 else None
        strongest_topic = max(topic_judgments, key=lambda item: ((item.support_score or 0), item.score)) if topic_judgments else None
        strained_topic = max(topic_judgments, key=lambda item: ((item.strain_score or 0), -item.score)) if topic_judgments else None
        if (
            strongest_topic
            and strained_topic
            and strongest_topic.key == strained_topic.key
            and len(topic_judgments) > 1
        ):
            strained_topic = sorted(topic_judgments, key=lambda item: ((item.strain_score or 0), -item.score), reverse=True)[1]

        rites = cls._planet_rite_lookup(ontology)
        thresholds = cls._threshold_lookup(ontology)
        title = "Daily horoscope"
        date_label = cls._format_calendar_label(transit_timestamp)

        if not top_contact:
            year_focus = cls._topic_phrase(year_map.activated_topics, 4) if year_map and year_map.activated_topics else "the themes your chart has already been repeating"
            payload = {
                "title": title,
                "date": date_label,
                "headline": "The sky is quieter today, so the yearly pattern matters more than a single dramatic trigger.",
                "overview": "Today is better read through the larger annual frame than through one dramatic transit trigger.",
                "focus": f"Keep your attention on {year_focus}. This is a steadier day for follow-through than for chasing fresh drama.",
                "opportunity": "Finish one practical task that supports the larger year theme.",
                "caution": "Do not mistake a quieter sky for a day with no meaning or no consequences.",
                "action": "Choose one unfinished matter tied to the bigger year theme and complete the next concrete step.",
                "main_transit": "No single transit is loud enough to dominate the day, which shifts the focus toward continuity, follow-through, and the larger story.",
                "day_thesis": f"Today is best used to stabilize {year_focus} rather than chase fresh drama.",
                "what_this_means": [
                    f"Emotionally, the day may feel less explosive and more reflective. That can be useful if you have been overstimulated, but it can also make avoidance look like peace.",
                    f"In practical life, this is a better day for finishing, reviewing, and organizing {year_focus} than for forcing a breakthrough.",
                    "Because there is no single dominant contact, intensity is lower, and your choices matter more than external pressure.",
                ],
                "why_the_chart_says_this": [
                    "A quiet transit sky does not mean the chart is empty. It means the daily weather is not overpowering the larger natal and yearly themes.",
                    "When no single transit is taking over, the annual profection, the lord of the year, and the natal condition carry more interpretive weight.",
                ],
                "larger_story": cls._annual_story_line(year_map, chart_data, "the active year"),
                "opportunities": [
                    "Finish one task that has been lingering in the background.",
                    "Review one plan, agreement, or habit before it becomes urgent.",
                    "Use the quieter tone of the day to choose deliberate action over emotional reaction.",
                ],
                "watch_fors": [
                    "Do not mistake low drama for clarity if you are still avoiding something important.",
                    "Avoid creating unnecessary stimulation just because the day feels less intense.",
                    "Watch for procrastination dressed up as waiting for a better moment.",
                ],
                "best_move_primary": "Choose one unfinished matter tied to the bigger year theme and complete the next concrete step.",
                "best_move_supporting": [
                    "Clear one practical obligation before starting anything new.",
                    "Name what the year keeps trying to teach you, then act in that direction once today.",
                ],
                "timing": "The current sky is relatively quiet, so timing favors steadiness, cleanup, and integration more than dramatic escalation.",
                "active_transits": [cls._transit_line(contact, ontology) for contact in contacts[:3]],
                "citations": cls._resolve_labels(["traditional_annual_profection", "traditional_solar_return", "traditional_fortune_spirit"]),
            }
            scores = cls._score_daily_horoscope(payload)
            payload = cls._revise_daily_horoscope(payload, scores, "The quieter sky still asks for interpretation through the natal and yearly frame.", TransitAspectRecord(
                transit_body="Sun",
                transit_sign="",
                transit_house=None,
                natal_body="Sun",
                natal_sign="",
                natal_house=None,
                type="Conjunction",
                degrees=0,
                orb=2.5,
            ))
            return DailyHoroscope(**payload)

        top_threshold = thresholds.get(top_contact.type, {})
        top_rite = rites.get(top_contact.transit_body, {})
        house_id = top_contact.natal_house or top_contact.transit_house
        house_number = cls._house_number(house_id)
        house_title = cls._house_title(ontology, house_id)
        house_plain_meaning = cls._house_plain_meaning(ontology, house_id)
        house_topics = cls._topic_phrase(cls._house_lived_topics(ontology, house_id), 6)
        second_clause = None
        if second_contact:
            second_clause = (
                f"A secondary influence comes from {second_contact.transit_body} {second_contact.type.lower()} "
                f"your {cls._display_body_name(second_contact.natal_body)}, which adds a second layer around "
                f"{cls._body_theme(second_contact.natal_body)}."
            )
        natal_condition_line = cls._natal_condition_line(chart_data, top_contact.natal_body)
        fortune_spirit_line = cls._fortune_spirit_line(chart_data)
        overlay_line = cls._overlay_line(top_threshold, top_rite)

        main_transit = cls._main_transit_summary(top_contact)
        day_thesis = cls._nonfatalistic(
            f"Today asks you to handle {house_title.lower()} with more awareness, because {top_contact.transit_body.lower()} is energizing {cls._display_body_name(top_contact.natal_body).lower()} matters instead of leaving them in the background."
        )
        what_this_means = [
            cls._nonfatalistic(
                f"Emotionally, this may feel like a rise in sensitivity around {cls._body_theme(top_contact.natal_body)}. "
                f"If the transit is supportive, you can feel more open, hopeful, or clear. If it is tense, you can feel pressed, exposed, impatient, or easier to trigger."
            ),
            cls._nonfatalistic(
                f"In lived experience, the transit is showing up through {house_title.lower()}, which includes {house_topics}. "
                f"{house_plain_meaning}"
            ),
            cls._nonfatalistic(cls._phase_and_orb_sentence(top_contact)),
        ]
        if second_clause:
            what_this_means.append(cls._nonfatalistic(second_clause))

        why_the_chart_says_this = [
            cls._nonfatalistic(
                f"{top_contact.transit_body} rules {cls._body_theme(top_contact.transit_body)}, while your natal {cls._display_body_name(top_contact.natal_body)} rules {cls._body_theme(top_contact.natal_body)}. "
                f"A {top_contact.type.lower()} {cls._aspect_plain_meaning(top_contact.type)}."
            ),
            cls._nonfatalistic(
                f"Because the contact lands through {house_title.lower()}, the symbolism becomes concrete through {house_topics} rather than staying abstract."
            ),
        ]
        if natal_condition_line:
            why_the_chart_says_this.append(cls._nonfatalistic(natal_condition_line))
        if overlay_line:
            why_the_chart_says_this.append(cls._nonfatalistic(overlay_line))

        larger_story = cls._nonfatalistic(cls._annual_story_line(year_map, chart_data, house_title))
        if fortune_spirit_line:
            larger_story = f"{larger_story} {cls._nonfatalistic(fortune_spirit_line)}".strip()

        opportunities = [cls._nonfatalistic(item) for item in cls._opportunity_lines(house_number, house_title, top_contact.transit_body, top_contact.natal_body)]
        if strongest_topic and (strongest_topic.support_score or 0) > 0:
            opportunities.append(cls._nonfatalistic(f"Lean on what is already working around {strongest_topic.title.lower()} instead of acting as if every part of life is under equal strain."))
        opportunities = opportunities[:4]

        watch_fors = [cls._nonfatalistic(item) for item in cls._watch_for_lines(house_number, top_contact.transit_body, top_contact.type)]
        if strained_topic and (strained_topic.strain_score or 0) > 0:
            watch_fors.append(cls._nonfatalistic(f"Do not let today's trigger spill into {strained_topic.title.lower()}, where the chart already shows extra pressure."))
        watch_fors = watch_fors[:4]

        best_move_primary = cls._nonfatalistic(
            year_map.guidance if year_map and year_map.guidance else f"Handle one real-world matter in {house_title.lower()} directly before the day ends."
        )
        best_move_supporting = [
            cls._nonfatalistic(opportunities[0]) if opportunities else "Take one grounded supporting step.",
            cls._nonfatalistic("Name the real issue in plain language before you answer it emotionally."),
        ]
        if house_number == 1:
            best_move_supporting.append("Clean up your appearance, body, or immediate environment before an important interaction.")
        elif house_number == 8:
            best_move_supporting.append("Have one mature conversation about money, trust, support, or obligation without turning it into catastrophe.")
        elif house_number == 11:
            best_move_supporting.append("Reach out to one ally with a concrete ask instead of hoping support appears on its own.")
        else:
            best_move_supporting.append("Choose one action that produces a visible result rather than a symbolic gesture.")

        timing = cls._nonfatalistic(cls._timing_sentence(top_contact, transit_timezone))
        active_transits = [cls._transit_line(contact, ontology) for contact in contacts[:5]]
        citation_ids = {
            *top_threshold.get("source_lens_tags", []),
            *top_rite.get("source_lens_tags", []),
            "traditional_annual_profection",
            "traditional_solar_return",
            "tetrabiblos_house_topic",
            "tetrabiblos_planetary_quality",
        }
        if strongest_topic:
            citation_ids.update(strongest_topic.citations)
        if strained_topic:
            citation_ids.update(strained_topic.citations)
        payload = {
            "title": title,
            "date": date_label,
            "headline": cls._nonfatalistic(
                f"{top_contact.transit_body} {top_contact.type.lower()} {cls._display_body_name(top_contact.natal_body)} sets the tone for {date_label.lower()}."
            ),
            "overview": cls._nonfatalistic(
                f"Today's chart is led by {top_contact.transit_body} {top_contact.type.lower()} {cls._display_body_name(top_contact.natal_body)}, which concentrates attention in {house_title.lower()}."
            ),
            "focus": cls._nonfatalistic(
                f"The practical focus today is {house_title.lower()}: {house_topics}. The immediate task is to respond consciously around {cls._body_theme(top_contact.natal_body)}."
            ),
            "opportunity": opportunities[0] if opportunities else best_move_primary,
            "caution": watch_fors[0] if watch_fors else "Do not let a passing transit become the whole story of the day.",
            "action": best_move_primary,
            "main_transit": cls._nonfatalistic(main_transit),
            "day_thesis": day_thesis,
            "what_this_means": what_this_means,
            "why_the_chart_says_this": why_the_chart_says_this,
            "larger_story": larger_story,
            "opportunities": opportunities,
            "watch_fors": watch_fors,
            "best_move_primary": best_move_primary,
            "best_move_supporting": best_move_supporting[:3],
            "timing": timing,
            "active_transits": active_transits,
            "action_checklist": cls._checklist_lines(best_move_primary, best_move_supporting, watch_fors),
            "citations": sorted(cls._resolve_labels(list(citation_ids))),
        }
        scores = cls._score_daily_horoscope(payload)
        payload = cls._revise_daily_horoscope(payload, scores, house_plain_meaning, top_contact)
        return DailyHoroscope(**payload)

    @classmethod
    def build_natal_prediction_cards(
        cls,
        contacts: List[TransitAspectRecord],
        transit_timestamp: str,
        transit_timezone: str,
        ontology: Dict,
        include_red_book_prompts: bool,
    ) -> List[PredictionCard]:
        rites = cls._planet_rite_lookup(ontology)
        thresholds = cls._threshold_lookup(ontology)
        if not contacts:
            return []

        top_contact = contacts[0]
        secondary_contact = contacts[1] if len(contacts) > 1 else top_contact
        lunar_contact = next((contact for contact in contacts if contact.transit_body == "Moon"), secondary_contact)
        top_threshold = thresholds.get(top_contact.type, {})
        secondary_threshold = thresholds.get(secondary_contact.type, {})
        top_rite = rites.get(top_contact.transit_body, {})
        secondary_rite = rites.get(secondary_contact.transit_body, {})
        lunar_rite = rites.get(lunar_contact.transit_body, {})

        return [
            PredictionCard(
                key="transit_current_weather",
                title="What is affecting you right now",
                timeframe=f"As of {transit_timestamp[:16].replace('T', ' ')} {transit_timezone}",
                summary=cls._contact_narrative(top_contact, ontology),
                opportunities=[
                    top_threshold.get("action", "Answer the transit with a precise act."),
                    *(top_rite.get("omens", [])[:1] or ["Follow the living signal instead of stale narrative."]),
                ],
                cautions=[
                    *(top_threshold.get("cautions", [])[:1] or ["reactivity"]),
                    *(top_rite.get("cautions", [])[:1] or ["over-identification"]),
                ],
                rituals=(top_rite.get("rituals", [])[:2] or ["Take one grounded, embodied action."]),
                citations=cls._resolve_labels([
                    *top_threshold.get("source_lens_tags", []),
                    *top_rite.get("source_lens_tags", []),
                ]),
            ),
            PredictionCard(
                key="transit_weekly_emphasis",
                title="What may matter most this week",
                timeframe="This week",
                summary=(
                    f"The next few days keep returning to {secondary_contact.transit_body} matters because "
                    f"{cls._contact_narrative(secondary_contact, ontology).lower()}"
                ),
                opportunities=[
                    *(secondary_rite.get("rituals", [])[:1] or ["Make the opening concrete."]),
                    secondary_threshold.get("display_name", secondary_contact.type),
                ],
                cautions=[
                    *(secondary_threshold.get("cautions", [])[:1] or ["wasted opportunity"]),
                    *(secondary_rite.get("cautions", [])[:1] or ["drift"]),
                ],
                rituals=(secondary_rite.get("rituals", [])[:2] or ["Turn the pattern into a practical schedule."]),
                citations=cls._resolve_labels([
                    *secondary_threshold.get("source_lens_tags", []),
                    *secondary_rite.get("source_lens_tags", []),
                ]),
            ),
            PredictionCard(
                key="transit_omen_threshold",
                title="What to notice and learn from",
                timeframe="Watch this threshold",
                summary=(
                    f"Keep a close eye on {lunar_contact.transit_body} material around {lunar_contact.natal_body}. "
                    f"{lunar_rite.get('jung_frame', 'The psyche is signaling through image before argument.')}"
                ),
                opportunities=[
                    *(lunar_rite.get("omens", [])[:2] or ["notice the recurring image", "follow the emotional signal"]),
                ],
                cautions=[
                    *(lunar_rite.get("cautions", [])[:2] or ["projection", "confusing atmosphere with evidence"]),
                ],
                rituals=(
                    [
                        *(lunar_rite.get("rituals", [])[:1] or ["Write down the image before you interpret it."]),
                        "Keep an omen log for seven days."
                    ]
                    if include_red_book_prompts else
                    (lunar_rite.get("rituals", [])[:2] or ["Keep an omen log for seven days."])
                ),
                citations=cls._resolve_labels([
                    *lunar_rite.get("source_lens_tags", []),
                    *( ["red_book_imaginal_prompt"] if include_red_book_prompts else [] ),
                ]),
            ),
        ]

    @classmethod
    def build_synastry_prediction_cards(
        cls,
        primary_profile: BirthProfile,
        secondary_profile: BirthProfile,
        primary_contacts: List[TransitAspectRecord],
        secondary_contacts: List[TransitAspectRecord],
        transit_timestamp: str,
        transit_timezone: str,
        ontology: Dict,
        include_red_book_prompts: bool,
    ) -> List[PredictionCard]:
        rites = cls._planet_rite_lookup(ontology)
        thresholds = cls._threshold_lookup(ontology)
        all_contacts = sorted(primary_contacts + secondary_contacts, key=cls._contact_priority)
        if not all_contacts:
            return []

        top_contact = all_contacts[0]
        partner_contact = next(
            (contact for contact in all_contacts if contact.natal_owner != top_contact.natal_owner),
            all_contacts[1] if len(all_contacts) > 1 else top_contact,
        )
        top_threshold = thresholds.get(top_contact.type, {})
        partner_threshold = thresholds.get(partner_contact.type, {})
        top_rite = rites.get(top_contact.transit_body, {})
        partner_rite = rites.get(partner_contact.transit_body, {})
        owner_label = primary_profile.name if top_contact.natal_owner == "primary" else secondary_profile.name
        other_label = secondary_profile.name if top_contact.natal_owner == "primary" else primary_profile.name
        partner_owner_label = primary_profile.name if partner_contact.natal_owner == "primary" else secondary_profile.name

        return [
            PredictionCard(
                key="synastry_transit_weather",
                title="What is affecting the relationship right now",
                timeframe=f"As of {transit_timestamp[:16].replace('T', ' ')} {transit_timezone}",
                summary=(
                    f"Right now, the strongest outside influence is {top_contact.transit_body} {top_contact.type.lower()} {owner_label}'s {cls._display_body_name(top_contact.natal_body)}. "
                    "Use that as a cue to respond thoughtfully instead of reacting on autopilot."
                ),
                opportunities=[
                    f"Let {owner_label} name the live pressure point first.",
                    *(top_rite.get("omens", [])[:1] or ["use the transit as a clarifying signal"]),
                ],
                cautions=[
                    *(top_threshold.get("cautions", [])[:1] or ["projection"]),
                    f"Do not make {other_label} carry an entire atmosphere that belongs to the moment.",
                ],
                rituals=(top_rite.get("rituals", [])[:2] or ["Have one exact clarifying conversation."]),
                citations=cls._resolve_labels([
                    *top_threshold.get("source_lens_tags", []),
                    *top_rite.get("source_lens_tags", []),
                ]),
            ),
            PredictionCard(
                key="synastry_transit_calibration",
                title="What both people may need to adjust",
                timeframe="This week",
                summary=(
                    f"A second live influence falls on {partner_owner_label}'s chart through {partner_contact.transit_body} {partner_contact.type.lower()} {cls._display_body_name(partner_contact.natal_body)}. "
                    f"This means both people are being asked to adjust, not just one."
                ),
                opportunities=[
                    partner_threshold.get("action", "Make the adjustment explicit."),
                    *(partner_rite.get("rituals", [])[:1] or ["Choose one practical relational agreement."]),
                ],
                cautions=[
                    *(partner_threshold.get("cautions", [])[:1] or ["splitting"]),
                    *(partner_rite.get("cautions", [])[:1] or ["drift"]),
                ],
                rituals=(partner_rite.get("rituals", [])[:2] or ["Set one explicit agreement for the week."]),
                citations=cls._resolve_labels([
                    *partner_threshold.get("source_lens_tags", []),
                    *partner_rite.get("source_lens_tags", []),
                ]),
            ),
            PredictionCard(
                key="synastry_transit_omen",
                title="What this moment may be teaching",
                timeframe="Watch this threshold",
                summary=(
                    "Notice which person carries the mood first and which person gives it a story. "
                    "Current transits suggest the relationship may reveal its truth through mirrored reactions before it reveals it through abstract discussion."
                ),
                opportunities=[
                    "Compare what each person is feeling with what each person is assuming.",
                    "Turn the recurring symbol or conflict into shared language."
                ],
                cautions=[
                    "projection",
                    "mistaking psychic intensity for agreement",
                ],
                rituals=(
                    [
                        f"{primary_profile.name} and {secondary_profile.name} each write one page on what this moment is asking for.",
                        "Read for image first, accusation second."
                    ] if include_red_book_prompts else [
                        "Each person states one need and one boundary clearly.",
                        "Revisit the agreement in seven days."
                    ]
                ),
                citations=cls._resolve_labels([
                    "levi_equilibrium",
                    "jung_projection_mirror",
                    *( ["red_book_imaginal_prompt"] if include_red_book_prompts else [] ),
                ]),
            ),
        ]
