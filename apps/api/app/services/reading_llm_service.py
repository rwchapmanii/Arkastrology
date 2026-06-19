from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.models.chart import DailyHoroscope, InterpretationBlock, ReadingSection
from app.services.env_service import load_local_env

load_local_env()

BASE_DIR = Path(__file__).resolve().parents[4]
SOURCE_OF_TRUTH_PATH = BASE_DIR / "docs" / "TRADITIONAL_ASTROLOGY_ALIGNMENT.md"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
LOGGER = logging.getLogger("the_ark.reading_llm")
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
HOUSE_TITLES = {
    1: "First House",
    2: "Second House",
    3: "Third House",
    4: "Fourth House",
    5: "Fifth House",
    6: "Sixth House",
    7: "Seventh House",
    8: "Eighth House",
    9: "Ninth House",
    10: "Tenth House",
    11: "Eleventh House",
    12: "Twelfth House",
}
HOUSE_TOPICS = {
    1: "body, identity, appearance, confidence, temperament, and first impressions",
    2: "money, livelihood, possessions, self-worth, and what you rely on materially",
    3: "communication, siblings, local movement, learning, and daily coordination",
    4: "home, family, roots, property, private life, and emotional foundations",
    5: "children, pleasure, romance, creativity, performance, play, and risk",
    6: "workload, health routines, service, maintenance, and daily strain",
    7: "partners, agreements, clients, contracts, and open conflict",
    8: "shared resources, debt, taxes, inheritances, trust, vulnerability, grief, and loss",
    9: "belief, study, teaching, travel, law, and meaning-making",
    10: "career, reputation, authority, public visibility, and responsibility",
    11: "friends, allies, audience, patrons, networks, and long-term hopes",
    12: "retreat, hidden pressures, isolation, private grief, and what stays behind the scenes",
}
PLANET_THEMES = {
    "Sun": "identity, vitality, purpose, visibility, and leadership",
    "Moon": "habit, mood, embodiment, memory, and emotional responsiveness",
    "Mercury": "thinking, speech, decisions, language, and interpretation",
    "Venus": "love, pleasure, agreement, value, beauty, and exchange",
    "Mars": "action, urgency, defense, conflict, and severing",
    "Jupiter": "growth, trust, protection, belief, coherence, and increase",
    "Saturn": "limits, duty, endurance, delay, consequence, and realism",
}
AXIS_LABELS = {
    frozenset({1, 7}): "self/other, identity/relationship, presentation/agreement",
    frozenset({2, 8}): "personal resources/shared resources, self-reliance/dependency, ownership/obligation",
    frozenset({3, 9}): "local knowledge/larger worldview, daily facts/bigger meaning",
    frozenset({4, 10}): "public/private, career/home, reputation/foundation",
    frozenset({5, 11}): "personal joy/collective hopes, children or creativity/friends or audience",
    frozenset({6, 12}): "visible labor/hidden burden, maintenance/retreat, duty/isolation",
}
INTERNAL_LABELS = {
    "reactive_complex": "reactive emotional pattern",
    "protection_vs_assertion": "the tension between self-protection and direct assertion",
}


def _openai_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def _reading_model() -> str:
    return (os.getenv("OPENAI_READING_MODEL") or "gpt-5-mini").strip()


def _reading_reasoning_effort() -> str:
    value = (os.getenv("OPENAI_READING_REASONING_EFFORT") or "low").strip().lower()
    return value if value in {"low", "medium", "high"} else "low"


def _reading_timeout_seconds() -> int:
    raw = (os.getenv("OPENAI_READING_TIMEOUT_SECONDS") or os.getenv("OPENAI_TIMEOUT_SECONDS") or "45").strip()
    try:
        value = int(raw)
    except ValueError:
        return 45
    return max(10, min(value, 120))


def _extract_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    output = payload.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text_value = part.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    text_parts.append(text_value.strip())
        if text_parts:
            return "\n\n".join(text_parts).strip()
    return ""


def _extract_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        candidate = candidate.replace("json", "", 1).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        match = JSON_BLOCK_RE.search(text)
        if not match:
            raise RuntimeError("Reading LLM returned no parseable JSON.")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Reading LLM returned invalid JSON.") from exc


def _clean_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_string_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = _clean_string(item)
        if text:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _clean_context_text(value: Any) -> Any:
    if isinstance(value, str):
        next_value = value
        for source, replacement in INTERNAL_LABELS.items():
            next_value = next_value.replace(source, replacement)
        return next_value
    if isinstance(value, list):
        return [_clean_context_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_context_text(item) for key, item in value.items()}
    return value


def _house_number(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value if 1 <= value <= 12 else None
    if isinstance(value, str) and value.lower().startswith("house"):
        try:
            number = int(value[5:])
        except ValueError:
            return None
        return number if 1 <= number <= 12 else None
    return None


def _house_title(value: Any) -> Optional[str]:
    number = _house_number(value)
    return HOUSE_TITLES.get(number)


def _house_topics(value: Any) -> Optional[str]:
    number = _house_number(value)
    return HOUSE_TOPICS.get(number)


def _planet_theme(name: Any) -> Optional[str]:
    if not isinstance(name, str):
        return None
    return PLANET_THEMES.get(name)


def _time_scale(transit_body: Any) -> str:
    return {
        "Moon": "hours",
        "Sun": "days",
        "Mercury": "days",
        "Venus": "days",
        "Mars": "weeks",
        "Jupiter": "weeks to months",
        "Saturn": "weeks to months",
    }.get(transit_body, "days")


def _topic_judgment_brief(topic: dict[str, Any]) -> dict[str, Any]:
    evidence_items = topic.get("evidence_items") or []
    support = (topic.get("supporting_evidence") or [item for item in evidence_items if item.get("polarity") == "support"])[:3]
    strain = (topic.get("challenging_evidence") or [item for item in evidence_items if item.get("polarity") == "strain"])[:3]
    activation = (topic.get("activating_evidence") or [item for item in evidence_items if item.get("polarity") == "activation"])[:3]
    mixed = [item for item in evidence_items if item.get("polarity") == "mixed"][:2]
    support_score = int(topic.get("support_score") or 0)
    strain_score = int(topic.get("strain_score") or 0)
    activation_score = int(topic.get("activation_score") or 0)
    label = str(topic.get("classification") or "mixed")
    if label == "difficult" and support_score >= strain_score:
        label = "mixed"
    return {
        "title": topic.get("title"),
        "classification": label,
        "confidence": topic.get("confidence"),
        "activation_score": activation_score,
        "support_score": support_score,
        "strain_score": strain_score,
        "supporting_testimony": [_clean_context_text(item.get("observation")) for item in support],
        "challenging_testimony": [_clean_context_text(item.get("observation")) for item in strain],
        "activation_testimony": [_clean_context_text(item.get("observation")) for item in activation],
        "mixed_testimony": [_clean_context_text(item.get("observation")) for item in mixed],
        "backend_synthesis": _clean_context_text(topic.get("synthesis")),
        "backend_validation_notes": _clean_context_text(topic.get("validation_notes") or []),
        "llm_guardrail": (
            "Treat this topic as clearly activated but not purely positive or purely negative."
            if label == "emphasized" else
            "Do not call this topic difficult unless the strain evidence is stronger than the support evidence."
            if support_score >= strain_score else
            "Name both the support and the friction instead of flattening the topic into one mood."
        ),
    }


def _fortune_spirit_context(chart_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    traditional = chart_data.get("traditional_context") or {}
    fortune = traditional.get("fortune") or {}
    spirit = traditional.get("spirit") or {}
    fortune_house = _house_number(fortune.get("house"))
    spirit_house = _house_number(spirit.get("house"))
    if not fortune_house or not spirit_house:
        return None
    relationship = "aligned"
    axis_label = None
    if fortune_house != spirit_house:
        if abs(fortune_house - spirit_house) == 6:
            relationship = "axis_split"
            axis_label = AXIS_LABELS.get(frozenset({fortune_house, spirit_house}))
        else:
            relationship = "distributed"
    return {
        "fortune_house": _house_title(fortune_house),
        "fortune_topics": _house_topics(fortune_house),
        "spirit_house": _house_title(spirit_house),
        "spirit_topics": _house_topics(spirit_house),
        "relationship": relationship,
        "axis_label": axis_label,
    }


def _detect_annual_patterns(technical_dump: dict[str, Any], chart_data: dict[str, Any]) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    annual = technical_dump.get("annual_profection") or {}
    solar_return = technical_dump.get("solar_return") or {}
    activated_house = _house_number(annual.get("activated_house"))
    lord_name = annual.get("lord_of_year")
    lord_house = _house_number(annual.get("lord_of_year_house"))
    solar_return_year_lord_house = _house_number(solar_return.get("year_lord_house"))
    solar_return_sun_house = _house_number(solar_return.get("sun_house"))
    if activated_house and lord_name and lord_house:
        patterns.append(
            {
                "name": "profection-routed-through-natal-lord-house",
                "summary": (
                    f"The profection activates the {HOUSE_TITLES[activated_house]}, and natal {lord_name} carries that year from the natal {HOUSE_TITLES[lord_house]}. "
                    f"That links {HOUSE_TOPICS[activated_house]} with {HOUSE_TOPICS[lord_house]}."
                ),
                "contexts": ["annual_profection", "natal"],
            }
        )
    if lord_name and lord_house and solar_return_year_lord_house:
        patterns.append(
            {
                "name": "natal-lord-house-repeated-in-solar-return",
                "summary": (
                    f"Natal {lord_name} carries the year from the natal {HOUSE_TITLES.get(lord_house, 'house')}, "
                    f"while the solar-return year lord lands in the solar-return {HOUSE_TITLES.get(solar_return_year_lord_house, 'house')}. "
                    "Keep those two houses in conversation instead of reading them as separate stories."
                ),
                "contexts": ["natal", "solar_return"],
            }
        )
    if solar_return.get("return_ascendant_sign") and solar_return_sun_house:
        patterns.append(
            {
                "name": "solar-return-atmosphere",
                "summary": (
                    f"The solar return rises in {solar_return['return_ascendant_sign']}, and the solar-return Sun falls in the "
                    f"{HOUSE_TITLES.get(solar_return_sun_house, 'house')}, bringing the year into {HOUSE_TOPICS.get(solar_return_sun_house, 'concrete lived experience')}."
                ),
                "contexts": ["solar_return"],
            }
        )
    fortune_spirit = _fortune_spirit_context(chart_data)
    if fortune_spirit and fortune_spirit.get("relationship") == "axis_split":
        patterns.append(
            {
                "name": "fortune-spirit-axis-split",
                "summary": (
                    f"Fortune and Spirit fall across a real axis: {fortune_spirit['fortune_house']} versus {fortune_spirit['spirit_house']}. "
                    f"This is a {fortune_spirit.get('axis_label') or 'life-axis split'}, so circumstance and chosen effort need to be coordinated consciously."
                ),
                "contexts": ["fortune_spirit"],
            }
        )
    return patterns[:4]


def _top_transit_contexts(transit_aspects: list[dict[str, Any]], chart_data: dict[str, Any], annual_profection: dict[str, Any]) -> list[dict[str, Any]]:
    planets = {item.get("id"): item for item in chart_data.get("planets") or [] if isinstance(item, dict)}
    activated_house = _house_number(annual_profection.get("activated_house"))
    contexts: list[dict[str, Any]] = []
    for contact in transit_aspects[:5]:
        natal_body = contact.get("natal_body")
        natal_planet = planets.get(natal_body, {})
        natal_house = _house_number(contact.get("natal_house") or natal_planet.get("house"))
        ruled_houses = [
            number for number in (natal_planet.get("rules_houses") or [])
            if isinstance(number, int) and 1 <= number <= 12
        ]
        annual_relevance = "low"
        if activated_house and (activated_house == natal_house or activated_house in ruled_houses):
            annual_relevance = "high"
        elif ruled_houses or natal_house:
            annual_relevance = "medium"
        contexts.append(
            {
                "transit": f"{contact.get('transit_body')} {str(contact.get('type') or '').lower()} natal {natal_body}",
                "phase": contact.get("phase"),
                "orb": contact.get("orb"),
                "time_scale": _time_scale(contact.get("transit_body")),
                "natal_planet_theme": _planet_theme(natal_body),
                "natal_house": _house_title(natal_house),
                "natal_house_topics": _house_topics(natal_house),
                "ruled_houses": [HOUSE_TITLES[number] for number in ruled_houses],
                "ruled_house_topics": [HOUSE_TOPICS[number] for number in ruled_houses[:3]],
                "annual_relevance": annual_relevance,
                "llm_hint": (
                    "Route this transit through the natal house and the houses the natal planet rules, not only through generic planet symbolism."
                ),
            }
        )
    return contexts


def _summarize_block(block: InterpretationBlock) -> dict[str, Any]:
    return {
        "title": _clean_context_text(block.title),
        "summary": _clean_context_text(block.summary),
        "plain_meaning": _clean_context_text(block.plain_meaning),
        "life_translation": _clean_context_text(block.life_translation),
        "why_this_matters": _clean_context_text(block.why_this_matters),
        "confidence": block.confidence,
        "source_tags": _clean_context_text(block.source_tags[:3]),
        "caveats": _clean_context_text(block.caveats[:2]),
        "citations": _clean_context_text(block.citations[:3]),
    }


@lru_cache(maxsize=1)
def _source_of_truth_text() -> str:
    if not SOURCE_OF_TRUTH_PATH.exists():
        return ""
    return SOURCE_OF_TRUTH_PATH.read_text(encoding="utf-8").strip()


def _build_context_payload(
    chart_type: str,
    reading: ReadingSection,
    daily_horoscope: Optional[DailyHoroscope],
    technical_summary: Any,
    interpretation_blocks: list[InterpretationBlock],
    prediction_cards: list[Any],
    source_lenses: list[Any],
) -> dict[str, Any]:
    technical_dump = technical_summary.model_dump() if technical_summary else {}
    chart_data = technical_dump.get("chart_data") or {}
    transit_aspects = technical_dump.get("transit_aspects") or []
    topic_judgments = technical_dump.get("topic_judgments") or []

    return {
        "chart_type": chart_type,
        "existing_reading": _clean_context_text(reading.model_dump()),
        "existing_daily_horoscope": _clean_context_text(daily_horoscope.model_dump()) if daily_horoscope else None,
        "chart_constraints": {
            "calculation_status": technical_dump.get("calculation_status"),
            "precision_mode": technical_dump.get("precision_mode"),
            "transit_timestamp": technical_dump.get("transit_timestamp"),
            "transit_timezone": technical_dump.get("transit_timezone"),
            "annual_profection": technical_dump.get("annual_profection"),
            "solar_return": technical_dump.get("solar_return"),
            "year_map": technical_dump.get("year_map"),
            "topic_judgments": topic_judgments[:5],
            "top_transits": transit_aspects[:5],
            "chart_highlights": {
                "sect": ((chart_data.get("traditional_context") or {}).get("sect")),
                "sect_light": ((chart_data.get("traditional_context") or {}).get("sect_light")),
                "fortune": ((chart_data.get("traditional_context") or {}).get("fortune")),
                "spirit": ((chart_data.get("traditional_context") or {}).get("spirit")),
            },
        },
        "llm_reasoning_aids": {
            "narration_constraints": [
                "Treat activation, support, and strain as separate concepts.",
                "Never call a topic difficult if the support evidence is equal to or stronger than the strain evidence.",
                "Always label natal placements separately from solar-return placements.",
                "Explain Fortune and Spirit concretely, especially when they split across an axis.",
                "Route transits through the natal planet's house and ruled houses, not only its generic planet meaning.",
                "Do not surface raw snake_case labels or internal taxonomy terms.",
            ],
            "topic_judgment_briefs": [_topic_judgment_brief(topic) for topic in topic_judgments[:6] if isinstance(topic, dict)],
            "annual_patterns": _detect_annual_patterns(technical_dump, chart_data),
            "fortune_spirit_context": _fortune_spirit_context(chart_data),
            "transit_context": _top_transit_contexts(transit_aspects, chart_data, technical_dump.get("annual_profection") or {}),
        },
        "interpretation_blocks": [_summarize_block(block) for block in interpretation_blocks[:6]],
        "prediction_cards": _clean_context_text([card.model_dump() for card in prediction_cards[:2]]),
        "source_lenses": _clean_context_text([lens.model_dump() for lens in source_lenses]),
    }


def _request_model(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    payload = {
        "model": _reading_model(),
        "reasoning": {"effort": _reading_reasoning_effort()},
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
    }

    request = urllib_request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_openai_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        LOGGER.info(
            "Reading LLM synthesis attempt. model=%s reasoning_effort=%s",
            _reading_model(),
            _reading_reasoning_effort(),
        )
        with urllib_request.urlopen(request, timeout=_reading_timeout_seconds()) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        LOGGER.warning("Reading LLM request failed with HTTP %s: %s", exc.code, error_body[:500])
        raise RuntimeError(f"Reading LLM request failed ({exc.code}).") from exc
    except urllib_error.URLError as exc:
        LOGGER.warning("Reading LLM request failed with URL error: %s", exc.reason)
        raise RuntimeError(f"Reading LLM request failed: {exc.reason}") from exc


class ReadingLLMService:
    @staticmethod
    def synthesize(
        *,
        chart_type: str,
        reading: ReadingSection,
        technical_summary: Any,
        interpretation_blocks: list[InterpretationBlock],
        source_lenses: list[Any],
        prediction_cards: list[Any],
        daily_horoscope: Optional[DailyHoroscope] = None,
    ) -> tuple[ReadingSection, Optional[DailyHoroscope], Optional[str]]:
        if not _openai_api_key():
            return reading, daily_horoscope, None

        context_payload = _build_context_payload(
            chart_type=chart_type,
            reading=reading,
            daily_horoscope=daily_horoscope,
            technical_summary=technical_summary,
            interpretation_blocks=interpretation_blocks,
            prediction_cards=prediction_cards,
            source_lenses=source_lenses,
        )

        system_prompt = (
            "You are The Ark's final reading voice. "
            "You do not calculate astrology; you translate supplied chart facts into better prose. "
            "The structured chart evidence and the source-of-truth document outrank your style instincts. "
            "Write elegant but practical astrology at about a 7th-10th grade reading level. "
            "Be specific, non-fatalistic, and grounded in traditional astrology first. "
            "Do not invent placements, timing, houses, citations, or confidence that are not in the input. "
            "Treat activation, support, and strain as different categories rather than flattening them into one mood. "
            "Always distinguish natal context from solar-return context when both are present. "
            "Never leak internal taxonomy labels, code-style names, or snake_case strings into the final prose. "
            "Optional Jungian or imaginal material must remain secondary if present. "
            "Return only valid JSON and no markdown."
        )

        user_prompt = (
            f"Source-of-truth document:\n{_source_of_truth_text()}\n\n"
            "Rewrite the final reading prose so it sounds like a serious astrologer instead of a template engine. "
            "Preserve the structure but improve clarity, specificity, warmth, and practical usefulness. "
            "Keep the reading honest about uncertainty. "
            "Use the llm_reasoning_aids as your first synthesis layer before falling back to longer prose blocks. "
            "If evidence is mixed, say so plainly. If a topic is emphasized, explain that it is louder without pretending it is automatically good or bad. "
            "If a daily horoscope is provided, rewrite it too.\n\n"
            "Return JSON with this exact shape:\n"
            "{\n"
            '  "reading": {\n'
            '    "headline": "string",\n'
            '    "practical_meaning": "string",\n'
            '    "life_translation": "string",\n'
            '    "guidance": "string",\n'
            '    "emotional_weather": "string or null",\n'
            '    "practical_focus": "string or null",\n'
            '    "primary_action": "string or null",\n'
            '    "supporting_actions": ["string"],\n'
            '    "avoid_pattern": "string or null",\n'
            '    "reflection_prompt": "string or null",\n'
            '    "check_in_question": "string or null",\n'
            '    "weather_context": "string or null",\n'
            '    "season_context": "string or null",\n'
            '    "climate_context": "string or null",\n'
            '    "prompt": "string or null",\n'
            '    "timing_focus": "string or null",\n'
            '    "ritual_focus": "string or null",\n'
            '    "oracle": "string or null"\n'
            "  },\n"
            '  "daily_horoscope": null or {\n'
            '    "title": "string",\n'
            '    "headline": "string",\n'
            '    "main_transit": "string or null",\n'
            '    "day_thesis": "string or null",\n'
            '    "what_this_means": ["string"],\n'
            '    "why_the_chart_says_this": ["string"],\n'
            '    "larger_story": "string or null",\n'
            '    "opportunities": ["string"],\n'
            '    "watch_fors": ["string"],\n'
            '    "best_move_primary": "string or null",\n'
            '    "best_move_supporting": ["string"],\n'
            '    "timing": "string",\n'
            '    "action_checklist": ["string"]\n'
            "  }\n"
            "}\n\n"
            f"Chart context JSON:\n{json.dumps(context_payload, ensure_ascii=True)}"
        )

        response_payload = _request_model(system_prompt, user_prompt)
        response_text = _extract_output_text(response_payload)
        if not response_text:
            raise RuntimeError("Reading LLM returned no answer text.")
        structured = _extract_json_object(response_text)

        reading_payload = structured.get("reading")
        if not isinstance(reading_payload, dict):
            raise RuntimeError("Reading LLM returned no reading object.")

        next_reading = reading.model_copy(
            update={
                "headline": _clean_string(reading_payload.get("headline")) or reading.headline,
                "practical_meaning": _clean_string(reading_payload.get("practical_meaning")) or reading.practical_meaning,
                "life_translation": _clean_string(reading_payload.get("life_translation")) or reading.life_translation,
                "guidance": _clean_string(reading_payload.get("guidance")) or reading.guidance,
                "emotional_weather": _clean_string(reading_payload.get("emotional_weather")) or reading.emotional_weather,
                "practical_focus": _clean_string(reading_payload.get("practical_focus")) or reading.practical_focus,
                "primary_action": _clean_string(reading_payload.get("primary_action")) or reading.primary_action,
                "supporting_actions": _clean_string_list(reading_payload.get("supporting_actions"), 4) or reading.supporting_actions,
                "avoid_pattern": _clean_string(reading_payload.get("avoid_pattern")) or reading.avoid_pattern,
                "reflection_prompt": _clean_string(reading_payload.get("reflection_prompt")) or reading.reflection_prompt,
                "check_in_question": _clean_string(reading_payload.get("check_in_question")) or reading.check_in_question,
                "weather_context": _clean_string(reading_payload.get("weather_context")) or reading.weather_context,
                "season_context": _clean_string(reading_payload.get("season_context")) or reading.season_context,
                "climate_context": _clean_string(reading_payload.get("climate_context")) or reading.climate_context,
                "prompt": _clean_string(reading_payload.get("prompt")) or reading.prompt,
                "timing_focus": _clean_string(reading_payload.get("timing_focus")) or reading.timing_focus,
                "ritual_focus": _clean_string(reading_payload.get("ritual_focus")) or reading.ritual_focus,
                "oracle": _clean_string(reading_payload.get("oracle")) or reading.oracle,
            }
        )

        next_daily = daily_horoscope
        daily_payload = structured.get("daily_horoscope")
        if daily_horoscope and isinstance(daily_payload, dict):
            opportunities = _clean_string_list(daily_payload.get("opportunities"), 4) or daily_horoscope.opportunities
            watch_fors = _clean_string_list(daily_payload.get("watch_fors"), 4) or daily_horoscope.watch_fors
            action_checklist = _clean_string_list(daily_payload.get("action_checklist"), 5) or daily_horoscope.action_checklist
            best_move_supporting = _clean_string_list(daily_payload.get("best_move_supporting"), 3) or daily_horoscope.best_move_supporting
            what_this_means = _clean_string_list(daily_payload.get("what_this_means"), 4) or daily_horoscope.what_this_means
            why_the_chart_says_this = _clean_string_list(daily_payload.get("why_the_chart_says_this"), 4) or daily_horoscope.why_the_chart_says_this
            best_move_primary = _clean_string(daily_payload.get("best_move_primary")) or daily_horoscope.best_move_primary
            day_thesis = _clean_string(daily_payload.get("day_thesis")) or daily_horoscope.day_thesis
            next_daily = daily_horoscope.model_copy(
                update={
                    "title": _clean_string(daily_payload.get("title")) or daily_horoscope.title,
                    "headline": _clean_string(daily_payload.get("headline")) or daily_horoscope.headline,
                    "main_transit": _clean_string(daily_payload.get("main_transit")) or daily_horoscope.main_transit,
                    "day_thesis": day_thesis,
                    "what_this_means": what_this_means,
                    "why_the_chart_says_this": why_the_chart_says_this,
                    "larger_story": _clean_string(daily_payload.get("larger_story")) or daily_horoscope.larger_story,
                    "opportunities": opportunities,
                    "watch_fors": watch_fors,
                    "best_move_primary": best_move_primary,
                    "best_move_supporting": best_move_supporting,
                    "timing": _clean_string(daily_payload.get("timing")) or daily_horoscope.timing,
                    "action_checklist": action_checklist,
                    "overview": what_this_means[0] if what_this_means else daily_horoscope.overview,
                    "focus": day_thesis or daily_horoscope.focus,
                    "opportunity": opportunities[0] if opportunities else daily_horoscope.opportunity,
                    "caution": watch_fors[0] if watch_fors else daily_horoscope.caution,
                    "action": best_move_primary or (action_checklist[0] if action_checklist else daily_horoscope.action),
                }
            )

        return next_reading, next_daily, _reading_model()
