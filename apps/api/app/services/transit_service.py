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
        return {
            "Sun": "identity, purpose, and visibility",
            "Moon": "emotions, habits, and embodiment",
            "Mercury": "thinking, speech, and decisions",
            "Venus": "love, pleasure, and value",
            "Mars": "action, pressure, and conflict",
            "Jupiter": "growth, belief, and opportunity",
            "Saturn": "duty, limits, and long-term structure",
            "Asc": "your outward style and first impression",
            "MC": "career, reputation, and direction",
        }.get(name, f"{name.lower()} matters")

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
        phase_bits = [contact.phase or None, f"orb {contact.orb:.1f}°"]
        return (
            f"{contact.transit_body} {contact.type.lower()} {cls._display_body_name(contact.natal_body)}"
            f" in {natal_house.lower()} ({' • '.join(bit for bit in phase_bits if bit)})"
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
    ) -> Optional[DailyHoroscope]:
        topic_judgments = topic_judgments or []
        transit_timezone = transit_timezone or "local time"
        top_contact = contacts[0] if contacts else None
        second_contact = contacts[1] if len(contacts) > 1 else None
        strongest_topic = max(topic_judgments, key=lambda item: item.score) if topic_judgments else None
        strained_topic = min(topic_judgments, key=lambda item: item.score) if topic_judgments else None
        if (
            strongest_topic
            and strained_topic
            and strongest_topic.key == strained_topic.key
            and len(topic_judgments) > 1
        ):
            strained_topic = sorted(topic_judgments, key=lambda item: item.score)[1]

        rites = cls._planet_rite_lookup(ontology)
        thresholds = cls._threshold_lookup(ontology)
        title = "Daily horoscope"
        date_label = cls._format_calendar_label(transit_timestamp)

        if not top_contact:
            year_focus = cls._topic_phrase(year_map.activated_topics, 3) if year_map and year_map.activated_topics else "the themes your chart is already repeating"
            return DailyHoroscope(
                title=title,
                date=date_label,
                headline="The day is quieter than the larger year pattern.",
                overview=(
                    f"Today is better read through the larger annual frame than through a single dramatic transit. "
                    f"The chart keeps returning to {year_focus}, so steady continuity matters more than sudden reaction."
                ),
                focus=(
                    f"Keep your attention on {year_focus}. This is a day for following what the chart has already put on your desk rather than chasing a brand-new signal."
                ),
                opportunity=year_map.guidance if year_map and year_map.guidance else "Consolidate what is already working before forcing new momentum.",
                caution="Do not assume a quiet sky means nothing is happening. Often it means the deeper annual story wants patience rather than drama.",
                action="Choose one concrete task that serves the larger year theme and finish it cleanly.",
                timing="The current sky is relatively quiet, so the best timing move is steadiness.",
                citations=cls._resolve_labels(["traditional_annual_profection", "traditional_solar_return", "traditional_fortune_spirit"]),
            )

        top_threshold = thresholds.get(top_contact.type, {})
        top_rite = rites.get(top_contact.transit_body, {})
        house_id = top_contact.natal_house or top_contact.transit_house
        house_title = cls._house_title(ontology, house_id)
        house_topics = cls._house_topics(ontology, house_id)
        year_clause = ""
        if year_map and year_map.activated_topics:
            year_clause = (
                f" Because your current year is already emphasizing {cls._topic_phrase(year_map.activated_topics, 3)}, "
                f"today's movement should be read as a live episode inside that larger storyline."
            )
        support_clause = (
            f" The easiest support still sits around {strongest_topic.title.lower()}."
            if strongest_topic and strongest_topic.score > 0 else ""
        )
        strain_clause = (
            f" The area needing the most care remains {strained_topic.title.lower()}."
            if strained_topic and strained_topic.score < 0 else ""
        )
        second_clause = ""
        if second_contact:
            second_clause = (
                f" A second influence comes from {second_contact.transit_body} {second_contact.type.lower()} "
                f"{cls._display_body_name(second_contact.natal_body)}, so the day is not one-note."
            )

        headline = f"{top_contact.transit_body} {top_contact.type.lower()} {cls._display_body_name(top_contact.natal_body)} sets the tone for {date_label.lower()}."
        overview = (
            f"Today's chart is led by {top_contact.transit_body} {top_contact.type.lower()} {cls._display_body_name(top_contact.natal_body)}. "
            f"This puts immediate pressure on {house_title.lower()}, especially {house_topics}.{year_clause}{support_clause}{strain_clause}"
        ).strip()
        focus = (
            f"The practical focus today is {house_title.lower()}: {house_topics}. "
            f"More specifically, the sky is asking for a conscious response around {cls._body_theme(top_contact.natal_body)}.{second_clause}"
        ).strip()
        opportunity = (
            f"{top_threshold.get('action', 'Answer the day with one precise act.')} "
            f"{(top_rite.get('omens', [])[:1] or ['Use the live signal instead of stale assumptions.'])[0].capitalize()}."
        )
        caution_seed = (top_threshold.get("cautions", [])[:1] or top_rite.get("cautions", [])[:1] or ["reactivity"])[0]
        caution = (
            f"Watch for {caution_seed} today. "
            + (
                f"The chart is already touchier around {strained_topic.title.lower()}, so do not let one trigger spill into the whole day."
                if strained_topic and strained_topic.score < 0 else
                "Do not let a passing transit harden into a total story about your life."
            )
        )
        action = (
            f"{(top_rite.get('rituals', [])[:1] or ['Take one grounded action that matches the chart.'])[0]} "
            + (
                f"Pair that with this year-guidance: {year_map.guidance}"
                if year_map and year_map.guidance else
                "Let the action be concrete, measured, and timely."
            )
        )
        timing = cls._timing_sentence(top_contact, transit_timezone)
        active_transits = [cls._transit_line(contact, ontology) for contact in contacts[:3]]
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
        return DailyHoroscope(
            title=title,
            date=date_label,
            headline=headline,
            overview=overview,
            focus=focus,
            opportunity=opportunity,
            caution=caution,
            action=action,
            timing=timing,
            active_transits=active_transits,
            citations=sorted(cls._resolve_labels(list(citation_ids))),
        )

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
