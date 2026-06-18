from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class AspectHit:
    type: str
    degrees: int
    orb: float


class AspectPolicyService:
    ASPECT_TARGETS: Dict[int, str] = {
        0: "Conjunction",
        60: "Sextile",
        90: "Square",
        120: "Trine",
        180: "Opposition",
    }
    BASE_ORBS = {
        "natal": {
            "Conjunction": 8.0,
            "Opposition": 8.0,
            "Trine": 7.0,
            "Square": 6.0,
            "Sextile": 5.0,
        },
        "synastry": {
            "Conjunction": 7.0,
            "Opposition": 7.0,
            "Trine": 6.0,
            "Square": 6.0,
            "Sextile": 4.5,
        },
        "transit": {
            "Conjunction": 3.0,
            "Opposition": 3.0,
            "Trine": 2.5,
            "Square": 2.5,
            "Sextile": 2.0,
        },
    }
    LUMINARY_BONUS = {
        "natal": 1.0,
        "synastry": 0.5,
        "transit": 0.25,
    }
    SUPPORTED_CONTEXTS = {"natal", "synastry", "transit"}
    LUMINARIES = {"Sun", "Moon"}

    @staticmethod
    def angular_difference(first: float, second: float) -> float:
        diff = abs(first - second) % 360.0
        return diff if diff <= 180.0 else 360.0 - diff

    @classmethod
    def max_orb(cls, first_body: str, second_body: str, aspect_type: str, context: str) -> float:
        if context not in cls.SUPPORTED_CONTEXTS:
            raise ValueError(f"Unsupported aspect context: {context}")
        base = cls.BASE_ORBS[context][aspect_type]
        luminary_hits = int(first_body in cls.LUMINARIES) + int(second_body in cls.LUMINARIES)
        return base + (luminary_hits * cls.LUMINARY_BONUS[context])

    @classmethod
    def detect_aspect(
        cls,
        first_body: str,
        first_longitude: float,
        second_body: str,
        second_longitude: float,
        context: str,
    ) -> Optional[AspectHit]:
        angle = cls.angular_difference(first_longitude, second_longitude)
        best_hit: Optional[AspectHit] = None
        best_sort: Optional[Tuple[float, int]] = None

        for degrees, label in cls.ASPECT_TARGETS.items():
            orb = abs(angle - degrees)
            if orb > cls.max_orb(first_body, second_body, label, context):
                continue
            candidate = AspectHit(type=label, degrees=degrees, orb=round(orb, 4))
            candidate_sort = (candidate.orb, degrees)
            if best_sort is None or candidate_sort < best_sort:
                best_hit = candidate
                best_sort = candidate_sort

        return best_hit
