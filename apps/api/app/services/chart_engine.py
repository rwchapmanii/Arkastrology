from typing import Dict, List

from flatlib import const
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos

from app.models.chart import AnglePlacement, AspectRecord, HousePlacement, NatalTechnicalChart
from app.services.aspect_service import AspectPolicyService
from app.services.astrology_settings import ANGLES, DEFAULT_HOUSE_SYSTEM, DEFAULT_HOUSE_SYSTEM_LABEL, MAJOR_PLANETS
from app.services.traditional_astrology_service import TraditionalAstrologyService


class ChartEngineError(Exception):
    pass


class NatalChartEngine:
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
        lat = cls._decimal_to_geo(latitude, 'n', 's')
        lon = cls._decimal_to_geo(longitude, 'e', 'w')
        return GeoPos(lat, lon)

    @staticmethod
    def _normalize_date(date_text: str) -> str:
        return date_text.replace('-', '/')

    @staticmethod
    def _normalize_time(time_text: str) -> str:
        if not time_text:
            return "12:00"
        return time_text[:5] if len(time_text) >= 5 else time_text

    @classmethod
    def _build_chart(cls, date_text: str, time_text: str, utc_offset: str, latitude: float, longitude: float) -> Chart:
        try:
            dt = Datetime(cls._normalize_date(date_text), cls._normalize_time(time_text), utc_offset)
            pos = cls._to_geopos(latitude, longitude)
            return Chart(dt, pos, hsys=DEFAULT_HOUSE_SYSTEM)
        except Exception as exc:
            raise ChartEngineError(str(exc)) from exc

    @classmethod
    def calculate_chart(cls, date_text: str, time_text: str, utc_offset: str, latitude: float, longitude: float) -> NatalTechnicalChart:
        chart = cls._build_chart(date_text, time_text, utc_offset, latitude, longitude)

        planets = TraditionalAstrologyService.enrich_planets(chart)
        angles: List[AnglePlacement] = []
        for angle_id in ANGLES:
            obj = chart.get(angle_id)
            angles.append(
                AnglePlacement(
                    id=obj.id,
                    sign=obj.sign,
                    sign_degree=round(obj.signlon, 4),
                    longitude=round(obj.lon, 4),
                )
            )

        houses: List[HousePlacement] = []
        for idx in range(1, 13):
            house_id = f"House{idx}"
            house = chart.houses.get(house_id)
            houses.append(
                HousePlacement(
                    id=house.id,
                    sign=house.sign,
                    sign_degree=round(house.signlon, 4),
                    longitude=round(house.lon, 4),
                )
            )

        aspects: List[AspectRecord] = []
        for i, first in enumerate(MAJOR_PLANETS):
            obj1 = chart.get(first)
            for second in MAJOR_PLANETS[i + 1:]:
                obj2 = chart.get(second)
                aspect = AspectPolicyService.detect_aspect(
                    first_body=obj1.id,
                    first_longitude=round(obj1.lon, 8),
                    second_body=obj2.id,
                    second_longitude=round(obj2.lon, 8),
                    context="natal",
                )
                if aspect:
                    aspects.append(
                        AspectRecord(
                            first=obj1.id,
                            second=obj2.id,
                            type=aspect.type,
                            degrees=aspect.degrees,
                            orb=aspect.orb,
                        )
                    )

        aspects.sort(key=lambda item: item.orb)
        traditional_context = TraditionalAstrologyService.build_traditional_context(chart, planets)

        return NatalTechnicalChart(
            house_system=DEFAULT_HOUSE_SYSTEM_LABEL,
            planets=planets,
            angles=angles,
            houses=houses,
            aspects=aspects,
            traditional_context=traditional_context,
        )

    @classmethod
    def calculate_natal_chart(cls, birth_date: str, birth_time: str, utc_offset: str, latitude: float, longitude: float) -> NatalTechnicalChart:
        return cls.calculate_chart(
            date_text=birth_date,
            time_text=birth_time,
            utc_offset=utc_offset,
            latitude=latitude,
            longitude=longitude,
        )

    @classmethod
    def calculate_planetary_fallback_chart(cls, birth_date: str, birth_time: str, utc_offset: str) -> NatalTechnicalChart:
        chart = cls._build_chart(birth_date, birth_time, utc_offset, 0.0, 0.0)

        planets = TraditionalAstrologyService.enrich_planetary_fallback_planets(chart)
        aspects: List[AspectRecord] = []
        for i, first in enumerate(MAJOR_PLANETS):
            obj1 = chart.get(first)
            for second in MAJOR_PLANETS[i + 1:]:
                obj2 = chart.get(second)
                aspect = AspectPolicyService.detect_aspect(
                    first_body=obj1.id,
                    first_longitude=round(obj1.lon, 8),
                    second_body=obj2.id,
                    second_longitude=round(obj2.lon, 8),
                    context="natal",
                )
                if aspect:
                    aspects.append(
                        AspectRecord(
                            first=obj1.id,
                            second=obj2.id,
                            type=aspect.type,
                            degrees=aspect.degrees,
                            orb=aspect.orb,
                        )
                    )

        aspects.sort(key=lambda item: item.orb)
        return NatalTechnicalChart(
            house_system="Planetary-only fallback",
            planets=planets,
            angles=[],
            houses=[],
            aspects=aspects,
            traditional_context=None,
        )
