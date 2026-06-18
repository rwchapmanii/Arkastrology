from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from flatlib import const
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.dignities import accidental, essential
from flatlib.geopos import GeoPos
from flatlib.props import object as object_props
from flatlib.tools import arabicparts

from app.models.chart import (
    AnnualProfectionRecord,
    BirthProfile,
    HouseRulerRecord,
    LotRecord,
    NatalTechnicalChart,
    PlanetPlacement,
    SolarReturnRecord,
    TraditionalContext,
)
from app.services.astrology_settings import MAJOR_PLANETS


class TraditionalAstrologyService:
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
    DOMICILE_RULERS = {
        "Aries": const.MARS,
        "Taurus": const.VENUS,
        "Gemini": const.MERCURY,
        "Cancer": const.MOON,
        "Leo": const.SUN,
        "Virgo": const.MERCURY,
        "Libra": const.VENUS,
        "Scorpio": const.MARS,
        "Sagittarius": const.JUPITER,
        "Capricorn": const.SATURN,
        "Aquarius": const.SATURN,
        "Pisces": const.JUPITER,
    }
    DAY_SECT_PLANETS = {const.SUN, const.JUPITER, const.SATURN}
    NIGHT_SECT_PLANETS = {const.MOON, const.VENUS, const.MARS}
    LUMINARIES = {const.SUN, const.MOON}
    RETROGRADE_EXEMPT = {const.SUN, const.MOON}
    STATIONARY_THRESHOLD = 0.03

    @classmethod
    def _house_condition(cls, house_number: int) -> str:
        if house_number in {1, 4, 7, 10}:
            return "angular"
        if house_number in {2, 5, 8, 11}:
            return "succedent"
        return "cadent"

    @classmethod
    def _sign_distance(cls, start_sign: str, end_sign: str) -> int:
        return (cls.SIGN_INDEX[end_sign] - cls.SIGN_INDEX[start_sign]) % 12

    @classmethod
    def _is_aversion(cls, start_sign: str, end_sign: str) -> bool:
        return cls._sign_distance(start_sign, end_sign) in {1, 5, 7, 11}

    @classmethod
    def _sect(cls, chart: Chart) -> str:
        return "day" if chart.isDiurnal() else "night"

    @classmethod
    def _sect_light(cls, chart: Chart) -> str:
        return const.SUN if chart.isDiurnal() else const.MOON

    @classmethod
    def _movement_status(cls, obj) -> str:
        speed = obj.lonspeed or 0.0
        if obj.id in cls.RETROGRADE_EXEMPT:
            return "direct"
        if abs(speed) < cls.STATIONARY_THRESHOLD:
            return "stationary"
        return "retrograde" if speed < 0 else "direct"

    @classmethod
    def _visibility_status(cls, obj, accidental_info: accidental.AccidentalDignity) -> str:
        if obj.id in cls.LUMINARIES:
            return "luminary"
        if accidental_info.isCazimi():
            return "cazimi"
        if accidental_info.isCombust():
            return "combust"
        if accidental_info.isUnderSun():
            return "under_beams"
        return "visible"

    @classmethod
    def _planetary_sect(cls, obj, chart_sect: str, accidental_info: accidental.AccidentalDignity) -> str:
        if obj.id == const.MERCURY:
            mercury_sect = "day" if accidental_info.orientality() == "Oriental" else "night"
            return "in_sect" if mercury_sect == chart_sect else "contrary_to_sect"
        if chart_sect == "day":
            return "in_sect" if obj.id in cls.DAY_SECT_PLANETS else "contrary_to_sect"
        return "in_sect" if obj.id in cls.NIGHT_SECT_PLANETS else "contrary_to_sect"

    @classmethod
    def _triplicity_role(cls, obj, essential_info: essential.EssentialInfo) -> Optional[str]:
        if essential_info.dayTrip == obj.id:
            return "day"
        if essential_info.nightTrip == obj.id:
            return "night"
        if essential_info.partTrip == obj.id:
            return "participating"
        return None

    @classmethod
    def _essential_dignities(cls, obj, essential_info: essential.EssentialInfo) -> Tuple[List[str], List[str], Optional[str]]:
        dignities: List[str] = []
        debilities: List[str] = []
        triplicity_role = cls._triplicity_role(obj, essential_info)

        if essential_info.ruler == obj.id:
            dignities.append("domicile")
        if essential_info.exalt == obj.id:
            dignities.append("exaltation")
        if triplicity_role:
            dignities.append("triplicity")
        if essential_info.term == obj.id:
            dignities.append("term")
        if essential_info.face == obj.id:
            dignities.append("face")

        if essential_info.exile == obj.id:
            debilities.append("detriment")
        if essential_info.fall == obj.id:
            debilities.append("fall")

        return dignities, debilities, triplicity_role

    @classmethod
    def _strength_score(
        cls,
        obj,
        essential_info: essential.EssentialInfo,
        accidental_info: accidental.AccidentalDignity,
        house_condition: Optional[str],
        sect_status: Optional[str],
        visibility_status: str,
    ) -> int:
        score = int(essential_info.score) + int(accidental_info.score())

        if house_condition == "angular":
            score += 1
        elif house_condition == "cadent":
            score -= 1

        if sect_status == "in_sect":
            score += 1
        elif sect_status == "contrary_to_sect":
            score -= 1

        if visibility_status == "cazimi":
            score += 2
        elif visibility_status == "combust":
            score -= 2
        elif visibility_status == "under_beams":
            score -= 1

        if obj.id not in cls.RETROGRADE_EXEMPT and (obj.lonspeed or 0.0) < 0:
            score -= 1

        return score

    @staticmethod
    def _strength_label(score: int) -> str:
        if score >= 5:
            return "strong"
        if score <= 0:
            return "weak"
        return "mixed"

    @staticmethod
    def _decimal_to_geo(value: float, positive_suffix: str, negative_suffix: str) -> str:
        abs_value = abs(value)
        degrees = int(abs_value)
        minutes = int(round((abs_value - degrees) * 60))
        if minutes == 60:
            degrees += 1
            minutes = 0
        suffix = positive_suffix if value >= 0 else negative_suffix
        return f"{degrees}{suffix}{minutes:02d}"

    @classmethod
    def _to_geopos(cls, latitude: float, longitude: float) -> GeoPos:
        lat = cls._decimal_to_geo(latitude, "n", "s")
        lon = cls._decimal_to_geo(longitude, "e", "w")
        return GeoPos(lat, lon)

    @staticmethod
    def _normalize_date(date_text: str) -> str:
        return date_text.replace("-", "/")

    @staticmethod
    def _normalize_time(time_text: str) -> str:
        return time_text[:5] if len(time_text) >= 5 else (time_text or "12:00")

    @staticmethod
    def _format_offset(dt: datetime) -> str:
        offset = dt.utcoffset() or timedelta(0)
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        total_minutes = abs(total_minutes)
        hours, minutes = divmod(total_minutes, 60)
        return f"{sign}{hours:02d}:{minutes:02d}"

    @classmethod
    def _build_chart_for_dt(cls, dt: datetime, latitude: float, longitude: float) -> Chart:
        chart_dt = Datetime(
            cls._normalize_date(dt.strftime("%Y-%m-%d")),
            cls._normalize_time(dt.strftime("%H:%M")),
            cls._format_offset(dt),
        )
        pos = cls._to_geopos(latitude, longitude)
        return Chart(chart_dt, pos, hsys=const.HOUSES_WHOLE_SIGN)

    @staticmethod
    def _signed_longitude_delta(current: float, target: float) -> float:
        return ((target - current + 540.0) % 360.0) - 180.0

    @classmethod
    def _resolve_solar_return_context(
        cls,
        profile: BirthProfile,
        resolved_timezone: Optional[str],
    ) -> Optional[Tuple[timezone | ZoneInfo, str, float, float, str]]:
        timezone_name = profile.current_timezone_name or resolved_timezone or profile.timezone_name
        if timezone_name:
            tzinfo = ZoneInfo(timezone_name)
            timezone_label = timezone_name
        else:
            timezone_label = profile.current_utc_offset or profile.utc_offset or "UTC"
            tzinfo = cls._fallback_timezone(profile.current_utc_offset or profile.utc_offset)

        if profile.current_latitude is not None and profile.current_longitude is not None:
            return tzinfo, timezone_label, profile.current_latitude, profile.current_longitude, "current_location"
        if profile.latitude is not None and profile.longitude is not None:
            return tzinfo, timezone_label, profile.latitude, profile.longitude, "birth_location_fallback"
        return None

    @classmethod
    def _build_house_rulers(cls, chart: Chart, placements_by_id: Dict[str, PlanetPlacement]) -> Tuple[List[HouseRulerRecord], Dict[str, List[int]]]:
        records: List[HouseRulerRecord] = []
        rules_houses: Dict[str, List[int]] = {planet_id: [] for planet_id in MAJOR_PLANETS}
        for house_number in range(1, 13):
            house = chart.houses.get(f"House{house_number}")
            ruler = cls.DOMICILE_RULERS[house.sign]
            rules_houses.setdefault(ruler, []).append(house_number)
            ruler_placement = placements_by_id.get(ruler)
            records.append(
                HouseRulerRecord(
                    house_number=house_number,
                    sign=house.sign,
                    ruler=ruler,
                    ruler_sign=ruler_placement.sign if ruler_placement else None,
                    ruler_house=ruler_placement.house if ruler_placement else None,
                    ruler_strength=ruler_placement.traditional_strength if ruler_placement else None,
                )
            )
        return records, rules_houses

    @classmethod
    def enrich_planets(cls, chart: Chart) -> List[PlanetPlacement]:
        chart_sect = cls._sect(chart)
        asc_sign = chart.get(const.ASC).sign
        planets: List[PlanetPlacement] = []

        for planet_id in MAJOR_PLANETS:
            obj = chart.get(planet_id)
            house = chart.houses.getObjectHouse(obj)
            house_number = int(house.id.replace("House", ""))
            essential_info = essential.EssentialInfo(obj)
            accidental_info = accidental.AccidentalDignity(obj, chart)
            dignities, debilities, triplicity_role = cls._essential_dignities(obj, essential_info)
            visibility_status = cls._visibility_status(obj, accidental_info)
            sect_status = cls._planetary_sect(obj, chart_sect, accidental_info)
            house_condition = cls._house_condition(house_number)
            strength_score = cls._strength_score(
                obj=obj,
                essential_info=essential_info,
                accidental_info=accidental_info,
                house_condition=house_condition,
                sect_status=sect_status,
                visibility_status=visibility_status,
            )
            planets.append(
                PlanetPlacement(
                    id=obj.id,
                    sign=obj.sign,
                    sign_degree=round(obj.signlon, 4),
                    longitude=round(obj.lon, 4),
                    house=house.id,
                    retrograde=obj.lonspeed < 0,
                    longitude_speed=round(obj.lonspeed, 6),
                    movement_status=cls._movement_status(obj),
                    house_condition=house_condition,
                    sect_status=sect_status,
                    visibility_status=visibility_status,
                    domicile_ruler=essential_info.ruler,
                    essential_dignities=dignities,
                    essential_debilities=debilities,
                    triplicity_role=triplicity_role,
                    term_ruler=essential_info.term,
                    face_ruler=essential_info.face,
                    in_house_joy=accidental_info.inHouseJoy(),
                    in_sign_joy=accidental_info.inSignJoy(),
                    aversion_to_ascendant=cls._is_aversion(asc_sign, obj.sign),
                    traditional_strength=cls._strength_label(strength_score),
                )
            )
        return planets

    @classmethod
    def enrich_planetary_fallback_planets(cls, chart: Chart) -> List[PlanetPlacement]:
        planets: List[PlanetPlacement] = []
        for planet_id in MAJOR_PLANETS:
            obj = chart.get(planet_id)
            essential_info = essential.EssentialInfo(obj)
            accidental_info = accidental.AccidentalDignity(obj, chart)
            dignities, debilities, triplicity_role = cls._essential_dignities(obj, essential_info)
            visibility_status = cls._visibility_status(obj, accidental_info)
            strength_score = int(essential_info.score)
            if visibility_status == "combust":
                strength_score -= 2
            elif visibility_status == "under_beams":
                strength_score -= 1
            elif visibility_status == "cazimi":
                strength_score += 2
            if obj.id not in cls.RETROGRADE_EXEMPT and (obj.lonspeed or 0.0) < 0:
                strength_score -= 1
            planets.append(
                PlanetPlacement(
                    id=obj.id,
                    sign=obj.sign,
                    sign_degree=round(obj.signlon, 4),
                    longitude=round(obj.lon, 4),
                    house=None,
                    retrograde=obj.lonspeed < 0,
                    longitude_speed=round(obj.lonspeed, 6),
                    movement_status=cls._movement_status(obj),
                    visibility_status=visibility_status,
                    domicile_ruler=essential_info.ruler,
                    essential_dignities=dignities,
                    essential_debilities=debilities,
                    triplicity_role=triplicity_role,
                    term_ruler=essential_info.term,
                    face_ruler=essential_info.face,
                    in_sign_joy=(object_props.signJoy.get(obj.id) == obj.sign),
                    traditional_strength=cls._strength_label(strength_score),
                )
            )
        return planets

    @classmethod
    def build_traditional_context(cls, chart: Chart, planets: List[PlanetPlacement]) -> TraditionalContext:
        placements_by_id = {planet.id: planet for planet in planets}
        house_rulers, rules_houses = cls._build_house_rulers(chart, placements_by_id)
        for planet in planets:
            planet.rules_houses = rules_houses.get(planet.id, [])

        asc = chart.get(const.ASC)
        asc_ruler = cls.DOMICILE_RULERS[asc.sign]
        asc_ruler_placement = placements_by_id.get(asc_ruler)

        def build_lot(name: str, formula: str, lot_id: str) -> Optional[LotRecord]:
            try:
                lot = arabicparts.getPart(lot_id, chart)
            except Exception:
                return None
            ruler = cls.DOMICILE_RULERS[lot.sign]
            ruler_placement = placements_by_id.get(ruler)
            house = chart.houses.getObjectHouse(lot)
            return LotRecord(
                name=name,
                formula=formula,
                sign=lot.sign,
                sign_degree=round(lot.signlon, 4),
                longitude=round(lot.lon, 4),
                house=house.id if house else None,
                ruler=ruler,
                ruler_sign=ruler_placement.sign if ruler_placement else None,
                ruler_house=ruler_placement.house if ruler_placement else None,
                ruler_strength=ruler_placement.traditional_strength if ruler_placement else None,
            )

        chart_sect = cls._sect(chart)
        fortune_formula = "Asc + Moon - Sun by day / Asc + Sun - Moon by night"
        spirit_formula = "Asc + Sun - Moon by day / Asc + Moon - Sun by night"

        return TraditionalContext(
            zodiac="tropical",
            sect=chart_sect,
            sect_light=cls._sect_light(chart),
            ascendant_sign=asc.sign,
            ascendant_degree=round(asc.signlon, 4),
            ascendant_ruler=asc_ruler,
            ascendant_ruler_sign=asc_ruler_placement.sign if asc_ruler_placement else None,
            ascendant_ruler_house=asc_ruler_placement.house if asc_ruler_placement else None,
            ascendant_ruler_strength=asc_ruler_placement.traditional_strength if asc_ruler_placement else None,
            house_rulers=house_rulers,
            fortune=build_lot("Fortune", fortune_formula, arabicparts.PARS_FORTUNA),
            spirit=build_lot("Spirit", spirit_formula, arabicparts.PARS_SPIRIT),
        )

    @staticmethod
    def _parse_birth_time(time_text: str) -> Tuple[int, int, int]:
        if not time_text:
            return 12, 0, 0
        parts = [int(part) for part in time_text.split(":")]
        while len(parts) < 3:
            parts.append(0)
        return parts[0], parts[1], parts[2]

    @staticmethod
    def _fallback_timezone(utc_offset: Optional[str]) -> timezone:
        if not utc_offset:
            return timezone.utc
        sign = 1 if utc_offset.startswith("+") else -1
        hours_text, minutes_text = utc_offset[1:].split(":")
        delta = timedelta(hours=int(hours_text), minutes=int(minutes_text))
        return timezone(sign * delta)

    @classmethod
    def _birthday_in_year(cls, profile: BirthProfile, year: int, tzinfo) -> datetime:
        birth_date = datetime.fromisoformat(profile.birth_date)
        hour, minute, second = cls._parse_birth_time(profile.birth_time)
        try:
            return datetime(year, birth_date.month, birth_date.day, hour, minute, second, tzinfo=tzinfo)
        except ValueError:
            return datetime(year, 2, 28, hour, minute, second, tzinfo=tzinfo)

    @classmethod
    def build_annual_profection(
        cls,
        profile: BirthProfile,
        chart_data: NatalTechnicalChart,
        reference_dt: Optional[datetime],
    ) -> Optional[AnnualProfectionRecord]:
        if not chart_data.houses or not chart_data.traditional_context or not chart_data.traditional_context.house_rulers:
            return None

        if reference_dt is None:
            reference_dt = datetime.now(cls._fallback_timezone(profile.utc_offset))
        elif reference_dt.tzinfo is None:
            reference_dt = reference_dt.replace(tzinfo=cls._fallback_timezone(profile.utc_offset))

        birth_year = int(profile.birth_date[:4])
        birthday_this_year = cls._birthday_in_year(profile, reference_dt.year, reference_dt.tzinfo)
        current_age = reference_dt.year - birth_year
        if reference_dt < birthday_this_year:
            current_age -= 1
            start_dt = cls._birthday_in_year(profile, reference_dt.year - 1, reference_dt.tzinfo)
            end_dt = birthday_this_year
        else:
            start_dt = birthday_this_year
            end_dt = cls._birthday_in_year(profile, reference_dt.year + 1, reference_dt.tzinfo)

        activated_house = (current_age % 12) + 1
        house = chart_data.houses[activated_house - 1]
        house_ruler = next(
            (item for item in chart_data.traditional_context.house_rulers if item.house_number == activated_house),
            None,
        )
        lord_placement = next(
            (planet for planet in chart_data.planets if house_ruler and planet.id == house_ruler.ruler),
            None,
        )

        return AnnualProfectionRecord(
            age=current_age,
            activated_house=activated_house,
            activated_sign=house.sign,
            lord_of_year=house_ruler.ruler if house_ruler else cls.DOMICILE_RULERS[house.sign],
            lord_of_year_sign=lord_placement.sign if lord_placement else None,
            lord_of_year_house=lord_placement.house if lord_placement else None,
            lord_of_year_strength=lord_placement.traditional_strength if lord_placement else None,
            starts_at=start_dt.isoformat(),
            ends_at=end_dt.isoformat(),
        )

    @classmethod
    def find_current_solar_return_datetime(
        cls,
        profile: BirthProfile,
        natal_chart: NatalTechnicalChart,
        reference_dt: Optional[datetime],
        resolved_timezone: Optional[str] = None,
    ) -> Optional[Tuple[int, datetime, str, float, float, str]]:
        natal_sun = next((planet for planet in natal_chart.planets if planet.id == const.SUN), None)
        context = cls._resolve_solar_return_context(profile, resolved_timezone)
        if not natal_sun or context is None:
            return None

        tzinfo, timezone_label, latitude, longitude, location_status = context
        local_reference = reference_dt.astimezone(tzinfo) if reference_dt else datetime.now(tzinfo)
        solar_year = local_reference.year
        birthday_seed = cls._birthday_in_year(profile, solar_year, tzinfo)
        if local_reference < birthday_seed:
            solar_year -= 1
            birthday_seed = cls._birthday_in_year(profile, solar_year, tzinfo)

        window_start = birthday_seed - timedelta(days=2)
        window_end = birthday_seed + timedelta(days=2)
        step = timedelta(hours=2)

        best_dt = birthday_seed
        best_abs_delta = float("inf")
        bracket: Optional[Tuple[datetime, float, datetime, float]] = None
        previous_dt: Optional[datetime] = None
        previous_delta: Optional[float] = None
        cursor = window_start
        while cursor <= window_end:
            chart = cls._build_chart_for_dt(cursor, latitude, longitude)
            sun = chart.get(const.SUN)
            delta = cls._signed_longitude_delta(sun.lon, natal_sun.longitude)
            abs_delta = abs(delta)
            if abs_delta < best_abs_delta:
                best_dt = cursor
                best_abs_delta = abs_delta
            if previous_delta is not None:
                if previous_delta == 0:
                    best_dt = previous_dt or cursor
                    bracket = None
                    break
                if delta == 0 or previous_delta * delta < 0:
                    bracket = (previous_dt or cursor, previous_delta, cursor, delta)
                    break
            previous_dt = cursor
            previous_delta = delta
            cursor += step

        if bracket is not None:
            left_dt, left_delta, right_dt, right_delta = bracket
            for _ in range(24):
                midpoint = left_dt + (right_dt - left_dt) / 2
                chart = cls._build_chart_for_dt(midpoint, latitude, longitude)
                mid_delta = cls._signed_longitude_delta(chart.get(const.SUN).lon, natal_sun.longitude)
                if abs(mid_delta) < best_abs_delta:
                    best_dt = midpoint
                    best_abs_delta = abs(mid_delta)
                if abs(mid_delta) <= 0.0005:
                    best_dt = midpoint
                    break
                if left_delta * mid_delta <= 0:
                    right_dt, right_delta = midpoint, mid_delta
                else:
                    left_dt, left_delta = midpoint, mid_delta
        else:
            for minutes in [60, 20, 5, 1]:
                improved = True
                while improved:
                    improved = False
                    for direction in (-1, 1):
                        candidate = best_dt + direction * timedelta(minutes=minutes)
                        chart = cls._build_chart_for_dt(candidate, latitude, longitude)
                        delta = abs(cls._signed_longitude_delta(chart.get(const.SUN).lon, natal_sun.longitude))
                        if delta + 1e-9 < best_abs_delta:
                            best_dt = candidate
                            best_abs_delta = delta
                            improved = True

        return solar_year, best_dt, timezone_label, latitude, longitude, location_status

    @classmethod
    def build_solar_return_record(
        cls,
        solar_year: int,
        annual_profection: Optional[AnnualProfectionRecord],
        solar_return_chart: NatalTechnicalChart,
        return_dt: datetime,
        timezone_label: str,
        location_status: str,
    ) -> SolarReturnRecord:
        asc = next((angle for angle in solar_return_chart.angles if angle.id == const.ASC), None)
        mc = next((angle for angle in solar_return_chart.angles if angle.id == const.MC), None)
        sun = next((planet for planet in solar_return_chart.planets if planet.id == const.SUN), None)
        year_lord = next(
            (
                planet for planet in solar_return_chart.planets
                if annual_profection and planet.id == annual_profection.lord_of_year
            ),
            None,
        )
        angular_planets = [
            planet.id
            for planet in solar_return_chart.planets
            if planet.house_condition == "angular"
        ]

        return SolarReturnRecord(
            solar_year=solar_year,
            return_timestamp=return_dt.isoformat(),
            return_timezone=timezone_label,
            location_status=location_status,
            return_ascendant_sign=asc.sign if asc else None,
            return_ascendant_degree=asc.sign_degree if asc else None,
            return_midheaven_sign=mc.sign if mc else None,
            return_midheaven_degree=mc.sign_degree if mc else None,
            sun_house=sun.house if sun else None,
            year_lord=annual_profection.lord_of_year if annual_profection else None,
            year_lord_house=year_lord.house if year_lord else None,
            year_lord_strength=year_lord.traditional_strength if year_lord else None,
            angular_planets=angular_planets,
        )
