from __future__ import annotations

from datetime import datetime
from typing import List

from app.models.chart import (
    NatalReadingRequest,
    NatalReadingResponse,
    PredictionCard,
    ReadingSection,
    SourceLens,
    TechnicalSummary,
)
from app.services.astrology_settings import DEFAULT_HOUSE_SYSTEM_LABEL
from app.services.chart_engine import ChartEngineError, NatalChartEngine
from app.services.content_loader import load_ontology
from app.services.interpretation_service import NatalInterpretationService
from app.services.profile_resolution_service import ProfileResolutionService
from app.services.traditional_astrology_service import TraditionalAstrologyService
from app.services.transit_service import TransitForecastService


class NatalReadingService:
    @staticmethod
    def _build_source_lenses(request: NatalReadingRequest) -> List[SourceLens]:
        source_lenses = [
            SourceLens(
                lens="traditional_core",
                labels=[
                    "Ancient and traditional core: whole-sign houses, seven visible planets, sect, and house rulerships",
                    "Ancient and traditional core: planetary condition, Fortune and Spirit, annual profections, and solar return timing",
                    "Traditional method: repeated testimony outweighs isolated placements",
                    "Traditional method: observation, rule, interpretation, confidence, and caveat are exposed as structured evidence in topic judgment",
                ],
            )
        ]

        source_lenses.append(
            SourceLens(
                lens="app_synthesis",
                labels=[
                    "App synthesis: explanatory language, confidence wording, and reading order are added on top of the traditional judgment",
                    "App synthesis: user-facing summaries must not override structural chart testimony",
                ],
            )
        )

        source_lenses.append(
            SourceLens(
                lens="current_sky",
                labels=[
                    "Supplemental current-sky layer: live transit chart anchored to present time and location",
                    "Supplemental current-sky layer: transits are not the full traditional time-lord stack",
                ],
            )
        )

        if request.include_jungian:
            source_lenses.append(
                SourceLens(
                    lens="modern_psychology",
                    labels=[
                        "Modern optional overlay: Jungian interpretation",
                        "Modern optional overlay: psychology does not override chart structure",
                    ],
                )
            )

        if request.include_red_book_prompts:
            source_lenses.append(
                SourceLens(
                    lens="modern_reflection",
                    labels=["Modern optional layer: imaginal and journaling prompts"],
                )
            )
        return source_lenses

    @staticmethod
    def build_response(request: NatalReadingRequest) -> NatalReadingResponse:
        ontology = load_ontology()
        counts = {key: len(value) for key, value in ontology.items()}
        source_lenses = NatalReadingService._build_source_lenses(request)
        prediction_cards: List[PredictionCard] = []
        interpretation_blocks = []
        notes = [
            f"Birth time precision received as: {request.profile.time_precision}.",
            "Astrology is treated here as a symbolic interpretive framework, not a scientifically proven diagnostic system.",
            "The Ark is being re-based on a traditional source-grounded doctrine: chart structure first, optional modern overlays second.",
            "Ontology ingestion is live from structured JSON inside The Ark repository.",
        ]

        profile, resolution_status, resolved_timezone = ProfileResolutionService.resolve_profile(request.profile, notes)

        chart_data = None
        transit_chart_data = None
        transit_aspects = []
        transit_timestamp = None
        transit_timezone = None
        transit_location_status = None
        annual_profection = None
        solar_return = None
        solar_return_chart_data = None
        topic_judgments = []
        year_map = None
        calculation_status = "needs_birth_coordinates"
        engine_status = "waiting_for_geodata"
        status = "contract_ready"
        reading = ReadingSection(
            headline="The Ark natal instrument is ready.",
            practical_meaning=(
                "The API can resolve birthplace inputs, calculate a natal chart, and return structured technical, ontological, and predictive output once sufficient birth context is present."
            ),
            life_translation=(
                "The Ark starts from traditional chart structure and only adds optional modern overlays when you ask for them."
            ),
            guidance=(
                "Provide accurate birth context so the prediction layer can become specific instead of generic."
            ),
            prompt=(
                "Which repeated chart testimonies deserve the most weight?"
                if not request.include_red_book_prompts
                else "What images or dream fragments seem to gather around the chart's strongest themes?"
            ),
            oracle="The Ark is waiting for enough birth context to name the live current.",
        )

        if request.profile.time_precision != "exact":
            if profile.utc_offset:
                try:
                    chart_data = NatalChartEngine.calculate_planetary_fallback_chart(
                        birth_date=profile.birth_date,
                        birth_time=profile.birth_time,
                        utc_offset=profile.utc_offset,
                    )
                    calculation_status = "planetary_fallback"
                    engine_status = "planetary_longitudes_ready"
                    status = "natal_planetary_fallback"
                    interpretation_blocks = NatalInterpretationService.build_planetary_fallback_blocks(
                        chart_data=chart_data,
                        ontology=ontology,
                        include_jungian=request.include_jungian,
                        include_red_book_prompts=request.include_red_book_prompts,
                    )
                    transit_chart_data, transit_timestamp, transit_timezone, transit_location_status = TransitForecastService.calculate_current_transit_chart(
                        profile=profile,
                        resolved_timezone=resolved_timezone,
                    )
                    transit_aspects = TransitForecastService.build_transit_contacts(
                        profile=profile,
                        transit_chart=transit_chart_data,
                        natal_chart=chart_data,
                        transit_timestamp=transit_timestamp,
                    )
                    transit_block = TransitForecastService.build_natal_transit_block(
                        contacts=transit_aspects,
                        transit_timestamp=transit_timestamp,
                        transit_timezone=transit_timezone,
                        ontology=ontology,
                    )
                    if transit_block:
                        interpretation_blocks.append(transit_block)
                    prediction_cards = TransitForecastService.build_natal_prediction_cards(
                        contacts=transit_aspects,
                        transit_timestamp=transit_timestamp,
                        transit_timezone=transit_timezone,
                        ontology=ontology,
                        include_red_book_prompts=request.include_red_book_prompts,
                    ) or NatalInterpretationService.build_planetary_fallback_prediction_cards(
                        chart_data=chart_data,
                        ontology=ontology,
                        include_red_book_prompts=request.include_red_book_prompts,
                    )
                    reading = NatalInterpretationService.build_planetary_fallback_reading_section(
                        chart_data=chart_data,
                        ontology=ontology,
                        include_jungian=request.include_jungian,
                        include_red_book_prompts=request.include_red_book_prompts,
                    )
                    notes.append("Birth time is not exact, so The Ark switched to planetary fallback mode: planets and inter-planet aspects remain visible, while natal houses and angles are intentionally suppressed.")
                except ChartEngineError as exc:
                    calculation_status = "calculation_error"
                    engine_status = "flatlib_swisseph_error"
                    status = "needs_exact_birth_time"
                    notes.append(f"Planetary fallback could not be calculated: {exc}")
            else:
                calculation_status = "needs_birth_timezone"
                engine_status = "waiting_for_timezone"
                status = "needs_exact_birth_time"
                notes.append("Birth time is not exact and a usable UTC offset is still missing, so even planetary fallback could not be calculated yet.")

        elif profile.latitude is not None and profile.longitude is not None and profile.utc_offset:
            try:
                chart_data = NatalChartEngine.calculate_natal_chart(
                    birth_date=profile.birth_date,
                    birth_time=profile.birth_time,
                    utc_offset=profile.utc_offset,
                    latitude=profile.latitude,
                    longitude=profile.longitude,
                )
                calculation_status = "calculated"
                engine_status = "flatlib_swisseph_ready"
                status = "natal_calculated"
                transit_chart_data, transit_timestamp, transit_timezone, transit_location_status = TransitForecastService.calculate_current_transit_chart(
                    profile=profile,
                    resolved_timezone=resolved_timezone,
                )
                transit_aspects = TransitForecastService.build_transit_contacts(
                    profile=profile,
                    transit_chart=transit_chart_data,
                    natal_chart=chart_data,
                    transit_timestamp=transit_timestamp,
                )
                annual_profection = TraditionalAstrologyService.build_annual_profection(
                    profile=profile,
                    chart_data=chart_data,
                    reference_dt=datetime.fromisoformat(transit_timestamp) if transit_timestamp else None,
                )
                solar_return_context = TraditionalAstrologyService.find_current_solar_return_datetime(
                    profile=profile,
                    natal_chart=chart_data,
                    reference_dt=datetime.fromisoformat(transit_timestamp) if transit_timestamp else None,
                    resolved_timezone=resolved_timezone,
                )
                if solar_return_context:
                    solar_return_year, solar_return_dt, solar_return_timezone, solar_return_latitude, solar_return_longitude, solar_return_location_status = solar_return_context
                    solar_return_chart_data = NatalChartEngine.calculate_chart(
                        date_text=solar_return_dt.strftime("%Y-%m-%d"),
                        time_text=solar_return_dt.strftime("%H:%M"),
                        utc_offset=TraditionalAstrologyService._format_offset(solar_return_dt),
                        latitude=solar_return_latitude,
                        longitude=solar_return_longitude,
                    )
                    solar_return = TraditionalAstrologyService.build_solar_return_record(
                        solar_year=solar_return_year,
                        annual_profection=annual_profection,
                        solar_return_chart=solar_return_chart_data,
                        return_dt=solar_return_dt,
                        timezone_label=solar_return_timezone,
                        location_status=solar_return_location_status,
                    )
                interpretation_blocks = NatalInterpretationService.build_blocks(
                    chart_data=chart_data,
                    ontology=ontology,
                    include_jungian=request.include_jungian,
                    include_red_book_prompts=request.include_red_book_prompts,
                    annual_profection=annual_profection,
                    solar_return=solar_return,
                )
                topic_judgments = NatalInterpretationService.build_topic_judgments(chart_data, ontology)
                year_map = NatalInterpretationService.build_year_map_record(
                    chart_data=chart_data,
                    ontology=ontology,
                    annual_profection=annual_profection,
                    solar_return=solar_return,
                )
                transit_block = TransitForecastService.build_natal_transit_block(
                    contacts=transit_aspects,
                    transit_timestamp=transit_timestamp,
                    transit_timezone=transit_timezone,
                    ontology=ontology,
                )
                if transit_block:
                    interpretation_blocks.append(transit_block)
                prediction_cards = NatalInterpretationService.build_prediction_cards(
                    chart_data=chart_data,
                    ontology=ontology,
                    include_jungian=request.include_jungian,
                    include_red_book_prompts=request.include_red_book_prompts,
                    annual_profection=annual_profection,
                    solar_return=solar_return,
                )
                reading = NatalInterpretationService.build_reading_section(
                    chart_data=chart_data,
                    ontology=ontology,
                    include_jungian=request.include_jungian,
                    include_red_book_prompts=request.include_red_book_prompts,
                    annual_profection=annual_profection,
                    solar_return=solar_return,
                )
                if prediction_cards:
                    reading.timing_focus = prediction_cards[0].summary
                    reading.ritual_focus = "; ".join(prediction_cards[0].rituals[:2]) if prediction_cards[0].rituals else reading.ritual_focus
                if transit_aspects and not reading.oracle:
                    top_transit = transit_aspects[0]
                    reading.oracle = f"The Ark names the live transit as {top_transit.transit_body.lower()} {top_transit.type.lower()} {top_transit.natal_body.lower()}."
                notes.append("Natal chart calculated successfully from the resolved birth context.")
                notes.append("Traditional context now includes sect, house rulers, Fortune/Spirit, planetary condition, annual profection, and a solar return overlay.")
                notes.append("Structured topic judgments now expose explicit evidence trails, confidence labels, and caveats rather than only prose summaries.")
                notes.append("Live transits are being treated as a supplemental timing layer after the natal traditional frame, not as the primary timing method.")
                if transit_timestamp and transit_timezone:
                    notes.append(f"Transit forecast anchored to {transit_timestamp[:16].replace('T', ' ')} {transit_timezone}.")
                if solar_return and solar_return.return_timestamp:
                    notes.append(f"Current solar return anchored to {solar_return.return_timestamp[:16].replace('T', ' ')} {solar_return.return_timezone}.")
                if transit_location_status == "birth_location_fallback":
                    notes.append("Transit houses currently fall back to the birth location because no separate current location was supplied.")
                elif transit_location_status == "missing_location":
                    notes.append("Transit location data was missing, so transit houses and angles should not be treated as high-confidence.")
            except ChartEngineError as exc:
                calculation_status = "calculation_error"
                engine_status = "flatlib_swisseph_error"
                notes.append(f"Chart engine error: {exc}")
        else:
            notes.append("Latitude, longitude, and UTC offset remain required for real natal calculation and prediction specificity.")

        return NatalReadingResponse(
            status=status,
            profile=profile,
            technical_summary=TechnicalSummary(
                calculation_status=calculation_status,
                engine_status=engine_status,
                available_ontology_counts=counts,
                house_system=chart_data.house_system if chart_data else DEFAULT_HOUSE_SYSTEM_LABEL,
                supported_planets=[planet["display_name"] for planet in ontology["planets"]],
                supported_aspects=[aspect["display_name"] for aspect in ontology["aspects"]],
                input_resolution_status=resolution_status,
                resolved_timezone=resolved_timezone,
                precision_mode="exact" if request.profile.time_precision == "exact" else "planetary_fallback",
                chart_data=chart_data,
                transit_timestamp=transit_timestamp,
                transit_timezone=transit_timezone,
                transit_location_status=transit_location_status,
                transit_chart_data=transit_chart_data,
                transit_aspects=transit_aspects,
                annual_profection=annual_profection,
                solar_return=solar_return,
                solar_return_chart_data=solar_return_chart_data,
                topic_judgments=topic_judgments,
                year_map=year_map,
            ),
            reading=reading,
            source_lenses=source_lenses,
            prediction_cards=prediction_cards,
            interpretation_blocks=interpretation_blocks,
            notes=notes,
        )
