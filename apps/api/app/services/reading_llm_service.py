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


def _summarize_block(block: InterpretationBlock) -> dict[str, Any]:
    return {
        "title": block.title,
        "summary": block.summary,
        "plain_meaning": block.plain_meaning,
        "life_translation": block.life_translation,
        "why_this_matters": block.why_this_matters,
        "confidence": block.confidence,
        "source_tags": block.source_tags[:3],
        "caveats": block.caveats[:2],
        "citations": block.citations[:3],
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
        "existing_reading": reading.model_dump(),
        "existing_daily_horoscope": daily_horoscope.model_dump() if daily_horoscope else None,
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
        "interpretation_blocks": [_summarize_block(block) for block in interpretation_blocks[:6]],
        "prediction_cards": [card.model_dump() for card in prediction_cards[:2]],
        "source_lenses": [lens.model_dump() for lens in source_lenses],
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
            "Optional Jungian or imaginal material must remain secondary if present. "
            "Return only valid JSON and no markdown."
        )

        user_prompt = (
            f"Source-of-truth document:\n{_source_of_truth_text()}\n\n"
            "Rewrite the final reading prose so it sounds like a serious astrologer instead of a template engine. "
            "Preserve the structure but improve clarity, specificity, warmth, and practical usefulness. "
            "Keep the reading honest about uncertainty. "
            "If a daily horoscope is provided, rewrite it too.\n\n"
            "Return JSON with this exact shape:\n"
            "{\n"
            '  "reading": {\n'
            '    "headline": "string",\n'
            '    "practical_meaning": "string",\n'
            '    "life_translation": "string",\n'
            '    "guidance": "string",\n'
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
