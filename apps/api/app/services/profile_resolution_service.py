from typing import List, Optional, Tuple

from app.models.chart import BirthProfile, PlaceResolveRequest
from app.services.place_service import PlaceResolutionError, PlaceResolutionService


class ProfileResolutionService:
    @staticmethod
    def resolve_profile(profile: BirthProfile, notes: List[str]) -> Tuple[BirthProfile, str, Optional[str]]:
        has_coords = profile.latitude is not None and profile.longitude is not None
        has_offset = bool(profile.utc_offset)

        if has_coords and has_offset:
            return profile, "manual", profile.timezone_name

        try:
            resolved = PlaceResolutionService.resolve(
                PlaceResolveRequest(
                    city=profile.birth_city,
                    country=profile.birth_country,
                    birth_date=profile.birth_date,
                    birth_time=profile.birth_time,
                )
            )
            resolved_place = resolved.resolved_place
            if not resolved_place:
                return profile, "manual_unresolved", profile.timezone_name

            updated = profile.model_copy(
                update={
                    "latitude": profile.latitude if profile.latitude is not None else resolved_place.latitude,
                    "longitude": profile.longitude if profile.longitude is not None else resolved_place.longitude,
                    "utc_offset": profile.utc_offset or resolved_place.utc_offset,
                    "timezone_name": profile.timezone_name or resolved_place.timezone_name,
                }
            )
            notes.extend(resolved.notes)
            notes.append("Birthplace inputs were auto-resolved from city/country and birth date context.")
            return updated, "auto_resolved", updated.timezone_name
        except PlaceResolutionError as exc:
            notes.append(f"Place resolution could not complete automatically: {exc}")
            return profile, "manual_unresolved", profile.timezone_name
