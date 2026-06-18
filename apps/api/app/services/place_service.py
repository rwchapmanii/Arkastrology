from datetime import datetime
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from app.models.chart import PlaceResolveRequest, PlaceResolveResponse, ResolvedPlace


class PlaceResolutionError(Exception):
    pass


class PlaceResolutionService:
    _geolocator = Nominatim(user_agent="the-ark-astrology-app")
    _timezone_finder = TimezoneFinder()

    @staticmethod
    def _normalize_time(time_text: Optional[str]) -> str:
        if not time_text:
            return "12:00"
        return time_text[:5] if len(time_text) >= 5 else time_text

    @staticmethod
    def _format_offset(total_seconds: Optional[float]) -> Optional[str]:
        if total_seconds is None:
            return None
        minutes = int(total_seconds // 60)
        sign = "+" if minutes >= 0 else "-"
        absolute = abs(minutes)
        hours = absolute // 60
        remainder = absolute % 60
        return f"{sign}{hours:02d}:{remainder:02d}"

    @classmethod
    def _offset_for_birth_context(
        cls,
        timezone_name: Optional[str],
        birth_date: Optional[str],
        birth_time: Optional[str],
    ) -> Optional[str]:
        if not timezone_name or not birth_date:
            return None
        time_value = cls._normalize_time(birth_time)
        local_dt = datetime.strptime(f"{birth_date} {time_value}", "%Y-%m-%d %H:%M")
        aware = local_dt.replace(tzinfo=ZoneInfo(timezone_name))
        return cls._format_offset(aware.utcoffset().total_seconds() if aware.utcoffset() else None)

    @staticmethod
    def _normalized(text: Optional[str]) -> str:
        return (text or "").strip().lower()

    @classmethod
    def _candidate_score(cls, location, request: PlaceResolveRequest) -> Tuple[int, float, str]:
        raw = getattr(location, "raw", {}) or {}
        address = raw.get("address", {}) or {}
        display_name = cls._normalized(getattr(location, "address", ""))
        requested_city = cls._normalized(request.city)
        requested_country = cls._normalized(request.country)

        locality_fields = [
            address.get("city"),
            address.get("town"),
            address.get("village"),
            address.get("municipality"),
            address.get("hamlet"),
            address.get("county"),
            address.get("state_district"),
            address.get("state"),
        ]
        normalized_localities = [cls._normalized(item) for item in locality_fields if item]
        normalized_country = cls._normalized(address.get("country"))
        score = 0

        if requested_country and normalized_country == requested_country:
            score += 12
        elif requested_country and requested_country in display_name:
            score += 8

        if requested_city and requested_city in normalized_localities:
            score += 16
        elif requested_city and requested_city in display_name:
            score += 10

        kind = cls._normalized(raw.get("type"))
        if kind in {"city", "administrative", "town", "village", "municipality"}:
            score += 3

        importance = float(raw.get("importance", 0.0) or 0.0)
        return score, importance, display_name

    @classmethod
    def _choose_candidate(cls, matches: List, request: PlaceResolveRequest):
        ranked = sorted(matches, key=lambda item: cls._candidate_score(item, request), reverse=True)
        return ranked[0], ranked

    @classmethod
    def resolve(cls, request: PlaceResolveRequest) -> PlaceResolveResponse:
        query = f"{request.city}, {request.country}"
        matches = cls._geolocator.geocode(query, exactly_one=False, limit=max(request.limit, 3), addressdetails=True)
        if not matches:
            raise PlaceResolutionError(f"No place match found for {query}.")
        location, ranked_matches = cls._choose_candidate(matches, request)

        ranked_places = []
        for match in ranked_matches[: request.limit]:
            timezone_name = cls._timezone_finder.timezone_at(lng=match.longitude, lat=match.latitude)
            utc_offset = cls._offset_for_birth_context(timezone_name, request.birth_date, request.birth_time)
            ranked_places.append(
                ResolvedPlace(
                    query=query,
                    normalized_name=match.address,
                    latitude=round(float(match.latitude), 6),
                    longitude=round(float(match.longitude), 6),
                    timezone_name=timezone_name,
                    utc_offset=utc_offset,
                )
            )

        timezone_name = cls._timezone_finder.timezone_at(lng=location.longitude, lat=location.latitude)
        utc_offset = cls._offset_for_birth_context(timezone_name, request.birth_date, request.birth_time)

        notes = [f"Coordinates resolved from city and country. Selected: {location.address}."]
        if len(ranked_matches) > 1:
            alternatives = "; ".join(match.address for match in ranked_matches[1:3])
            notes.append(f"Multiple place matches existed, so the best city-level candidate was chosen automatically. Verify if you meant a different locality. Alternatives: {alternatives}.")
        if timezone_name:
            notes.append(f"Timezone resolved as {timezone_name}.")
        if utc_offset:
            notes.append(f"UTC offset resolved for the birth date as {utc_offset}.")
        else:
            notes.append("UTC offset could not be derived from the supplied birth date/time context.")

        return PlaceResolveResponse(
            status="resolved",
            resolved_place=ResolvedPlace(
                query=query,
                normalized_name=location.address,
                latitude=round(float(location.latitude), 6),
                longitude=round(float(location.longitude), 6),
                timezone_name=timezone_name,
                utc_offset=utc_offset,
            ),
            place_candidates=ranked_places,
            notes=notes,
        )
