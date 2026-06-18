from flatlib import const

DEFAULT_HOUSE_SYSTEM = const.HOUSES_WHOLE_SIGN
DEFAULT_HOUSE_SYSTEM_LABEL = "Whole Sign"

MAJOR_PLANETS = [
    const.SUN,
    const.MOON,
    const.MERCURY,
    const.VENUS,
    const.MARS,
    const.JUPITER,
    const.SATURN,
]

ANGLES = [const.ASC, const.MC]

ASPECT_TYPE_MAP = {
    0: "Conjunction",
    60: "Sextile",
    90: "Square",
    120: "Trine",
    180: "Opposition",
}
