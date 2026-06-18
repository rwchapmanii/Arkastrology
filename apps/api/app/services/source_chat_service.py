from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.models.chat import GroundedChatRequest, GroundedChatResponse, GroundedChatSource
from app.services.env_service import load_local_env

load_local_env()

BASE_DIR = Path(__file__).resolve().parents[4]
DOCS_DIR = BASE_DIR / "docs"
ONTOLOGY_DIR = BASE_DIR / "content" / "ontology"

TOKEN_RE = re.compile(r"[a-z0-9]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "how", "i",
    "in", "is", "it", "me", "my", "of", "on", "or", "so", "that", "the", "their", "them",
    "there", "these", "this", "to", "what", "when", "where", "which", "why", "with", "you",
    "your", "here", "does", "do", "can", "about", "into", "than", "then",
}
ALIASES = {
    "asc": "ascendant",
    "mc": "midheaven",
    "lot": "fortune spirit",
    "lots": "fortune spirit",
    "profections": "annual profection",
    "profection": "annual profection",
    "yearlord": "lord of the year",
    "year-lord": "lord of the year",
    "sectlight": "sect light",
}
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
LOGGER = logging.getLogger("the_ark.source_chat")


@dataclass(frozen=True)
class CorpusChunk:
    key: str
    title: str
    text: str
    source_type: str
    source_layer: Optional[str] = None
    source_ref: Optional[str] = None

    @property
    def search_text(self) -> str:
        return f"{self.title} {self.text}".strip()


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text.replace("`", "").replace("*", "")).strip()
    return text


def _normalize_answer_text(text: str) -> str:
    text = text.replace("\r", "")
    paragraphs = [re.sub(r"[ \t]+", " ", part).strip() for part in text.split("\n")]
    paragraphs = [part for part in paragraphs if part]
    return "\n\n".join(paragraphs).strip()


def _sentence_limit(text: str, max_sentences: int = 2, max_chars: int = 420) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    sentences = [part.strip() for part in SENTENCE_RE.split(cleaned) if part.strip()]
    if not sentences:
        return cleaned[:max_chars].rstrip() + ("…" if len(cleaned) > max_chars else "")
    joined = " ".join(sentences[:max_sentences])
    if len(joined) <= max_chars:
        return joined
    return joined[: max_chars - 1].rstrip() + "…"


def _openai_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def _openai_model() -> str:
    return (os.getenv("OPENAI_CHAT_MODEL") or "gpt-5.5").strip()


def _openai_reasoning_effort() -> str:
    value = (os.getenv("OPENAI_REASONING_EFFORT") or "high").strip().lower()
    return value if value in {"low", "medium", "high"} else "high"


def _openai_timeout_seconds() -> int:
    raw = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "45").strip()
    try:
        value = int(raw)
    except ValueError:
        return 45
    return max(10, min(value, 120))


def _normalize_token(token: str) -> str:
    expanded = ALIASES.get(token, token)
    if " " in expanded:
        return expanded
    if len(expanded) > 4 and expanded.endswith("s"):
        expanded = expanded[:-1]
    return expanded


def _tokenize(text: str) -> list[str]:
    raw_tokens = TOKEN_RE.findall(text.lower())
    expanded: list[str] = []
    for raw in raw_tokens:
        normalized = _normalize_token(raw)
        if " " in normalized:
            expanded.extend(part for part in normalized.split() if part and part not in STOPWORDS)
        elif normalized and normalized not in STOPWORDS:
            expanded.append(normalized)
    return expanded


def _markdown_chunks(path: Path, source_ref: str) -> list[CorpusChunk]:
    lines = path.read_text(encoding="utf-8").splitlines()
    chunks: list[CorpusChunk] = []
    heading = path.stem.replace("_", " ")
    paragraph_lines: list[str] = []
    chunk_index = 0

    def flush_paragraph() -> None:
        nonlocal chunk_index, paragraph_lines
        if not paragraph_lines:
            return
        text = _clean_text(" ".join(paragraph_lines))
        if text:
            chunks.append(
                CorpusChunk(
                    key=f"{source_ref}:{chunk_index}",
                    title=heading,
                    text=text,
                    source_type="source_document",
                    source_layer="traditional_core",
                    source_ref=source_ref,
                )
            )
            chunk_index += 1
        paragraph_lines = []

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_paragraph()
            continue
        if line.startswith("#"):
            flush_paragraph()
            heading = line.lstrip("#").strip() or heading
            continue
        if line.startswith("- "):
            flush_paragraph()
            bullet = line[2:].strip()
            if bullet:
                chunks.append(
                    CorpusChunk(
                        key=f"{source_ref}:{chunk_index}",
                        title=heading,
                        text=bullet,
                        source_type="source_document",
                        source_layer="traditional_core",
                        source_ref=source_ref,
                    )
                )
                chunk_index += 1
            continue
        paragraph_lines.append(line)

    flush_paragraph()
    return chunks


def _json_chunks(path: Path, source_ref: str) -> list[CorpusChunk]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    chunks: list[CorpusChunk] = []
    for index, item in enumerate(payload):
        title = str(item.get("display_name") or item.get("label") or item.get("collection") or item.get("id") or f"Item {index + 1}")
        if path.name == "houses.json":
            text = (
                f"{title} covers the classical topics {', '.join(item.get('classical_topics', []))}. "
                f"It is a {item.get('angularity_type', 'house')} house. "
                f"Modern fallback topics are {', '.join(item.get('modern_topics', []))}."
            )
            source_layer = "traditional_core"
        elif path.name == "planets.json":
            text = (
                f"{title} has the classical nature {', '.join(item.get('classical_nature', []))}. "
                f"It is {item.get('sect_affinity', 'mixed')} by sect and commonly signifies {', '.join(item.get('core_topics', []))}."
            )
            source_layer = "traditional_core"
        elif path.name == "aspects.json":
            text = (
                f"{title} is the {item.get('geometry_degrees')}° aspect. "
                f"It belongs to the {item.get('aspect_family', 'aspect')} family and is generally treated as {item.get('default_harmony_tension', 'meaningful')}."
            )
            source_layer = "traditional_core"
        elif path.name == "signs.json":
            text = (
                f"{title} is ruled by {item.get('ruler', 'its ruler')} and is associated with "
                f"{', '.join(item.get('classical_topics', []) or item.get('qualities', []))}."
            )
            source_layer = "traditional_core"
        elif path.name == "doctrine-layers.json":
            text = f"{title} belongs to the {item.get('layer', 'source')} layer. {item.get('notes', '')}".strip()
            source_layer = item.get("layer")
        elif path.name == "citations.json":
            text = f"{item.get('label', title)} is tagged under the {item.get('lens', 'source')} source lens."
            source_layer = item.get("lens")
        else:
            text = json.dumps(item, ensure_ascii=True)
            source_layer = None

        chunks.append(
            CorpusChunk(
                key=f"{source_ref}:{index}",
                title=title,
                text=_clean_text(text),
                source_type="ontology",
                source_layer=source_layer,
                source_ref=source_ref,
            )
        )
    return chunks


@lru_cache(maxsize=1)
def _load_source_corpus() -> tuple[CorpusChunk, ...]:
    chunks: list[CorpusChunk] = []
    chunks.extend(_markdown_chunks(DOCS_DIR / "TRADITIONAL_ASTROLOGY_ALIGNMENT.md", "docs/TRADITIONAL_ASTROLOGY_ALIGNMENT.md"))
    for name in ("doctrine-layers.json", "houses.json", "planets.json", "aspects.json", "signs.json", "citations.json"):
        chunks.extend(_json_chunks(ONTOLOGY_DIR / name, f"content/ontology/{name}"))
    return tuple(chunks)


def _extract_follow_up_context(question: str, history: list[dict[str, str]]) -> str:
    question_tokens = _tokenize(question)
    if len(question_tokens) >= 4:
        return question
    prior_user_turns = [turn["content"] for turn in history if turn.get("role") == "user" and turn.get("content")]
    if not prior_user_turns:
        return question
    return f"{prior_user_turns[-1]} {question}".strip()


def _build_reading_chunks(reading_payload: Optional[dict[str, Any]]) -> list[CorpusChunk]:
    if not reading_payload:
        return []
    chunks: list[CorpusChunk] = []
    reading = reading_payload.get("reading") or {}
    interpretation_blocks = reading_payload.get("interpretation_blocks") or []
    chart_type = reading_payload.get("chart_type") or "reading"

    opening_bits = [
        reading.get("headline"),
        reading.get("practical_meaning"),
        reading.get("life_translation"),
        reading.get("guidance"),
    ]
    opening_text = _clean_text(" ".join(bit for bit in opening_bits if isinstance(bit, str) and bit.strip()))
    if opening_text:
        chunks.append(
            CorpusChunk(
                key="reading:opening",
                title=f"Current {chart_type} reading",
                text=opening_text,
                source_type="current_reading",
                source_layer="app_synthesis",
                source_ref="current_reading",
            )
        )

    for index, block in enumerate(interpretation_blocks):
        text_bits: list[str] = []
        for key in ("plain_meaning", "summary", "life_translation", "traditional_doctrine", "confidence_explainer", "why_this_matters"):
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                text_bits.append(value.strip())
        chart_evidence = block.get("chart_evidence") or []
        if isinstance(chart_evidence, list):
            text_bits.extend(str(item).strip() for item in chart_evidence if str(item).strip())
        block_text = _clean_text(" ".join(text_bits))
        if not block_text:
            continue
        chunks.append(
            CorpusChunk(
                key=f"reading:block:{index}",
                title=str(block.get("title") or block.get("block_type") or f"Reading block {index + 1}"),
                text=block_text,
                source_type="current_reading",
                source_layer="app_synthesis",
                source_ref="current_reading",
            )
        )
    return chunks


def _format_history_for_model(history: list[dict[str, str]]) -> str:
    if not history:
        return "No prior conversation turns."
    lines: list[str] = []
    for turn in history[-6:]:
        role = str(turn.get("role") or "user").capitalize()
        content = _clean_text(str(turn.get("content") or ""))
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "No prior conversation turns."


def _format_chunks_for_model(chunks: list[CorpusChunk]) -> str:
    if not chunks:
        return "None."
    formatted: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        source_bits = [chunk.source_type]
        if chunk.source_layer:
            source_bits.append(chunk.source_layer)
        if chunk.source_ref:
            source_bits.append(chunk.source_ref)
        formatted.append(
            f"[{index}] {chunk.title} ({' | '.join(source_bits)})\n{_sentence_limit(chunk.text, max_sentences=4, max_chars=900)}"
        )
    return "\n\n".join(formatted)


def _score_chunk(question_tokens: set[str], question_text: str, chunk: CorpusChunk) -> float:
    search_text = chunk.search_text.lower()
    chunk_tokens = set(_tokenize(search_text))
    overlap = question_tokens & chunk_tokens
    score = float(len(overlap) * 4)

    title_tokens = set(_tokenize(chunk.title))
    score += float(len(question_tokens & title_tokens) * 2)

    if question_text in search_text:
        score += 8
    elif any(token in search_text for token in question_tokens):
        score += 1

    if chunk.source_type == "current_reading":
        score += 1.5
    if chunk.source_layer == "traditional_core":
        score += 0.5
    return score


def _rank_chunks(question: str, chunks: Iterable[CorpusChunk], history: list[dict[str, str]]) -> list[CorpusChunk]:
    effective_question = _extract_follow_up_context(question, history)
    question_text = _clean_text(effective_question).lower()
    question_tokens = set(_tokenize(question_text))
    if not question_tokens:
        return []

    scored: list[tuple[float, CorpusChunk]] = []
    for chunk in chunks:
        score = _score_chunk(question_tokens, question_text, chunk)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored]


def _dedupe_sources(chunks: list[CorpusChunk], limit: int = 4) -> list[GroundedChatSource]:
    seen: set[tuple[str, str]] = set()
    sources: list[GroundedChatSource] = []
    for chunk in chunks:
        marker = (chunk.title, chunk.source_ref or "")
        if marker in seen:
            continue
        seen.add(marker)
        sources.append(
            GroundedChatSource(
                title=chunk.title,
                excerpt=_sentence_limit(chunk.text, max_sentences=2, max_chars=240),
                source_type=chunk.source_type,
                source_layer=chunk.source_layer,
                source_ref=chunk.source_ref,
            )
        )
        if len(sources) >= limit:
            break
    return sources


def _fallback_answer(question: str, reading_chunks: list[CorpusChunk], doc_chunks: list[CorpusChunk]) -> str:
    paragraphs: list[str] = []

    if reading_chunks:
        reading_line = _sentence_limit(reading_chunks[0].text, max_sentences=2, max_chars=420)
        paragraphs.append(f"In your current reading, {reading_line[0].lower() + reading_line[1:] if len(reading_line) > 1 else reading_line}")

    if doc_chunks:
        if len(doc_chunks) == 1:
            paragraphs.append(
                f"The source documents ground that answer in this traditional rule: {_sentence_limit(doc_chunks[0].text, max_sentences=2, max_chars=420)}"
            )
        else:
            first = _sentence_limit(doc_chunks[0].text, max_sentences=1, max_chars=220)
            second = _sentence_limit(doc_chunks[1].text, max_sentences=1, max_chars=220)
            paragraphs.append(
                "The source documents support that answer in two ways: "
                f"{first} {second}"
            )

    if not paragraphs:
        return (
            "I could not ground a confident answer from the current reading and source documents yet. "
            "Try asking about a planet, house, annual profection, Fortune, Spirit, transits, or a specific sentence from the reading."
        )

    return "\n\n".join(paragraphs)


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


def _reasoned_answer(question: str, history: list[dict[str, str]], reading_chunks: list[CorpusChunk], doc_chunks: list[CorpusChunk]) -> str:
    api_key = _openai_api_key()
    if not api_key:
        LOGGER.info("Grounded chat using deterministic fallback because OPENAI_API_KEY is not configured.")
        return _fallback_answer(question, reading_chunks, doc_chunks)

    system_prompt = (
        "You are The Ark, an articulate traditional astrologer. "
        "Answer the user's specific question directly and naturally, not like a template or database dump. "
        "Ground your answer in the provided source material and reading context. "
        "Use high-level reasoning to synthesize the answer, but do not invent facts beyond the supplied context. "
        "Prefer traditional astrology framing over modern psychological drift unless the provided context explicitly requires a modern overlay. "
        "Do not repeat the whole reading. Answer only what helps with the question. "
        "If the evidence is mixed, say so plainly. If the context is insufficient, say what is missing."
    )

    user_prompt = (
        f"User question:\n{question}\n\n"
        f"Recent conversation turns:\n{_format_history_for_model(history)}\n\n"
        f"Current reading context:\n{_format_chunks_for_model(reading_chunks[:5])}\n\n"
        f"Traditional source documents and ontology:\n{_format_chunks_for_model(doc_chunks[:6])}\n\n"
        "Write a concise but articulate answer in plain prose, as a serious astrologer would."
    )

    payload = {
        "model": _openai_model(),
        "reasoning": {"effort": _openai_reasoning_effort()},
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
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        LOGGER.info(
            "Grounded chat attempting model synthesis. model=%s reasoning_effort=%s reading_chunks=%s doc_chunks=%s",
            _openai_model(),
            _openai_reasoning_effort(),
            len(reading_chunks),
            len(doc_chunks),
        )
        with urllib_request.urlopen(request, timeout=_openai_timeout_seconds()) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        LOGGER.warning("Grounded chat model request failed with HTTP %s: %s", exc.code, error_body[:500])
        raise RuntimeError(f"Grounded chat model request failed ({exc.code}): {error_body[:240]}") from exc
    except urllib_error.URLError as exc:
        LOGGER.warning("Grounded chat model request failed with URL error: %s", exc.reason)
        raise RuntimeError(f"Grounded chat model request failed: {exc.reason}") from exc

    answer = _extract_output_text(response_payload)
    if not answer:
        LOGGER.warning("Grounded chat model returned no answer text.")
        raise RuntimeError("Grounded chat model returned no answer text.")
    LOGGER.info("Grounded chat model synthesis succeeded.")
    return _normalize_answer_text(answer)


def _compose_answer(question: str, reading_chunks: list[CorpusChunk], doc_chunks: list[CorpusChunk]) -> str:
    return _fallback_answer(question, reading_chunks, doc_chunks)


class SourceChatService:
    @classmethod
    def answer_question(cls, request: GroundedChatRequest) -> GroundedChatResponse:
        question = _clean_text(request.question)
        history_payload = [turn.model_dump() for turn in request.history]
        reading_chunks = _build_reading_chunks(request.reading_payload)
        ranked_reading = _rank_chunks(question, reading_chunks, history_payload)
        ranked_docs = _rank_chunks(question, _load_source_corpus(), history_payload)

        top_reading = ranked_reading[:2]
        top_docs = ranked_docs[:3]
        notes = [
            "This answer is grounded in the current reading plus the traditional source documents loaded into The Ark.",
            "Optional symbolic or psychological overlays are not treated as the default source layer unless they are explicitly present in the reading context.",
        ]
        LOGGER.info(
            "Grounded chat received question. history_turns=%s reading_matches=%s doc_matches=%s question=%r",
            len(history_payload),
            len(top_reading),
            len(top_docs),
            question[:200],
        )

        try:
            answer = _reasoned_answer(question, history_payload, top_reading, top_docs)
            if _openai_api_key():
                notes.append(f"Reasoning model used: {_openai_model()}.")
        except RuntimeError as exc:
            answer = _compose_answer(question, top_reading, top_docs)
            notes.append(str(exc))
            notes.append("The system fell back to deterministic grounded synthesis for this answer.")
            LOGGER.warning("Grounded chat fell back to deterministic synthesis: %s", exc)

        sources = _dedupe_sources([*top_reading, *top_docs])
        if not top_docs:
            notes.append("The source-document match was weak, so the answer leaned more heavily on the current reading context.")

        return GroundedChatResponse(
            status="ok",
            answer=answer,
            sources=sources,
            grounding_notes=notes,
        )
