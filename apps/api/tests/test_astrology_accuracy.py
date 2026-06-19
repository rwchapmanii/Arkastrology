import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

import swisseph as swe

from app.models.chart import BirthProfile, NatalReadingRequest, PlaceResolveRequest, SynastryReadingRequest
from app.services.aspect_service import AspectPolicyService
from app.services.chart_engine import NatalChartEngine
from app.services.natal_service import NatalReadingService
from app.services.place_service import PlaceResolutionService
from app.services.synastry_service import SynastryReadingService
from app.services.traditional_astrology_service import TraditionalAstrologyService


class AstrologyAccuracyTests(unittest.TestCase):
    def build_profile(self, **overrides):
        base = {
            "name": "Ron",
            "birth_date": "1979-01-01",
            "birth_time": "12:00",
            "birth_city": "Detroit",
            "birth_country": "USA",
            "time_precision": "exact",
            "latitude": 42.3314,
            "longitude": -83.0458,
            "utc_offset": "-05:00",
            "timezone_name": "America/Detroit",
        }
        base.update(overrides)
        return BirthProfile(**base)

    def _julday_for_profile(self, profile: BirthProfile) -> float:
        local_dt = datetime.fromisoformat(f"{profile.birth_date}T{profile.birth_time or '12:00'}{profile.utc_offset}")
        utc_dt = local_dt.astimezone(timezone.utc)
        return swe.julday(
            utc_dt.year,
            utc_dt.month,
            utc_dt.day,
            utc_dt.hour + (utc_dt.minute / 60.0) + (utc_dt.second / 3600.0),
        )

    def test_aspect_policy_is_context_sensitive(self):
        natal_hit = AspectPolicyService.detect_aspect("Sun", 0.0, "Saturn", 7.5, "natal")
        transit_hit = AspectPolicyService.detect_aspect("Sun", 0.0, "Saturn", 7.5, "transit")
        self.assertIsNotNone(natal_hit)
        self.assertEqual(natal_hit.type, "Conjunction")
        self.assertIsNone(transit_hit)

    def test_chart_engine_golden_chart(self):
        chart = NatalChartEngine.calculate_chart(
            date_text="1979-01-01",
            time_text="12:00",
            utc_offset="-05:00",
            latitude=42.3314,
            longitude=-83.0458,
        )
        placements = {planet.id: planet for planet in chart.planets}
        angles = {angle.id: angle for angle in chart.angles}

        self.assertEqual(placements["Sun"].sign, "Capricorn")
        self.assertAlmostEqual(placements["Sun"].longitude, 280.6875, places=3)
        self.assertEqual(placements["Moon"].sign, "Aquarius")
        self.assertAlmostEqual(placements["Moon"].longitude, 321.3247, places=3)
        self.assertEqual(angles["Asc"].sign, "Aries")
        self.assertAlmostEqual(angles["Asc"].longitude, 4.8597, places=3)
        self.assertTrue(any(aspect.first == "Sun" and aspect.second == "Mars" and aspect.type == "Conjunction" for aspect in chart.aspects))

    def test_chart_engine_matches_swisseph_reference(self):
        profile = self.build_profile()
        chart = NatalChartEngine.calculate_chart(
            date_text=profile.birth_date,
            time_text=profile.birth_time,
            utc_offset=profile.utc_offset,
            latitude=profile.latitude,
            longitude=profile.longitude,
        )
        placements = {planet.id: planet for planet in chart.planets}
        angles = {angle.id: angle for angle in chart.angles}
        jd = self._julday_for_profile(profile)

        sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
        moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]
        mercury_lon = swe.calc_ut(jd, swe.MERCURY)[0][0]
        _, ascmc = swe.houses_ex(jd, profile.latitude, profile.longitude, b"W")

        self.assertAlmostEqual(placements["Sun"].longitude, sun_lon, places=3)
        self.assertAlmostEqual(placements["Moon"].longitude, moon_lon, places=3)
        self.assertAlmostEqual(placements["Mercury"].longitude, mercury_lon, places=3)
        self.assertAlmostEqual(angles["Asc"].longitude, ascmc[0], delta=0.02)
        self.assertAlmostEqual(angles["MC"].longitude, ascmc[1], delta=0.02)

    def test_exact_chart_exposes_traditional_context(self):
        chart = NatalChartEngine.calculate_chart(
            date_text="1979-01-01",
            time_text="12:00",
            utc_offset="-05:00",
            latitude=42.3314,
            longitude=-83.0458,
        )
        placements = {planet.id: planet for planet in chart.planets}
        context = chart.traditional_context

        self.assertIsNotNone(context)
        self.assertEqual(context.sect, "day")
        self.assertEqual(context.sect_light, "Sun")
        self.assertEqual(context.ascendant_sign, "Aries")
        self.assertEqual(context.ascendant_ruler, "Mars")
        self.assertEqual(context.fortune.house, "House2")
        self.assertEqual(context.spirit.house, "House11")
        self.assertEqual(placements["Sun"].sect_status, "in_sect")
        self.assertIn("exaltation", placements["Mars"].essential_dignities)
        self.assertEqual(placements["Saturn"].house_condition, "cadent")
        self.assertEqual(placements["Mars"].rules_houses, [1, 8])

    def test_annual_profection_uses_fixed_reference_date(self):
        profile = self.build_profile()
        chart = NatalChartEngine.calculate_chart(
            date_text=profile.birth_date,
            time_text=profile.birth_time,
            utc_offset=profile.utc_offset,
            latitude=profile.latitude,
            longitude=profile.longitude,
        )
        reference_dt = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        profection = TraditionalAstrologyService.build_annual_profection(profile, chart, reference_dt)

        self.assertIsNotNone(profection)
        self.assertEqual(profection.age, 47)
        self.assertEqual(profection.activated_house, 12)
        self.assertEqual(profection.activated_sign, "Pisces")
        self.assertEqual(profection.lord_of_year, "Jupiter")
        self.assertEqual(profection.lord_of_year_house, "House5")
        self.assertEqual(profection.lord_of_year_strength, "strong")

    def test_solar_return_uses_current_solar_year_even_when_local_return_is_previous_calendar_day(self):
        profile = self.build_profile()
        chart = NatalChartEngine.calculate_chart(
            date_text=profile.birth_date,
            time_text=profile.birth_time,
            utc_offset=profile.utc_offset,
            latitude=profile.latitude,
            longitude=profile.longitude,
        )
        reference_dt = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        result = TraditionalAstrologyService.find_current_solar_return_datetime(
            profile=profile,
            natal_chart=chart,
            reference_dt=reference_dt,
            resolved_timezone=profile.timezone_name,
        )

        self.assertIsNotNone(result)
        solar_year, return_dt, timezone_label, latitude, longitude, location_status = result
        self.assertEqual(solar_year, 2026)
        self.assertEqual(timezone_label, "America/Detroit")
        self.assertEqual(location_status, "birth_location_fallback")
        self.assertEqual(return_dt.year, 2025)
        self.assertEqual(return_dt.month, 12)
        self.assertEqual(return_dt.day, 31)
        self.assertAlmostEqual(latitude, profile.latitude, places=3)
        self.assertAlmostEqual(longitude, profile.longitude, places=3)

    def test_natal_approximate_time_uses_planetary_fallback(self):
        profile = self.build_profile(time_precision="approximate")
        response = NatalReadingService.build_response(NatalReadingRequest(profile=profile))
        self.assertEqual(response.status, "natal_planetary_fallback")
        self.assertIsNotNone(response.technical_summary.chart_data)
        self.assertEqual(response.technical_summary.chart_data.house_system, "Planetary-only fallback")
        self.assertFalse(response.technical_summary.chart_data.angles)
        self.assertFalse(response.technical_summary.chart_data.houses)
        self.assertEqual(response.technical_summary.precision_mode, "planetary_fallback")

    def test_natal_uses_current_transit_location_when_supplied(self):
        profile = self.build_profile(
            current_latitude=34.0522,
            current_longitude=-118.2437,
            current_timezone_name="America/Los_Angeles",
            current_utc_offset="-07:00",
        )
        response = NatalReadingService.build_response(NatalReadingRequest(profile=profile))
        self.assertEqual(response.status, "natal_calculated")
        self.assertEqual(response.technical_summary.transit_location_status, "current_location")
        self.assertTrue(response.technical_summary.transit_aspects)
        self.assertIsNotNone(response.technical_summary.transit_chart_data)
        contact = response.technical_summary.transit_aspects[0]
        self.assertIn(contact.phase, {"applying", "separating", "exact", "steady"})
        self.assertIsNotNone(contact.exact_at)
        self.assertIsNotNone(contact.peak_window_start)
        self.assertIsNotNone(contact.peak_window_end)
        exact_at = datetime.fromisoformat(contact.exact_at)
        peak_window_start = datetime.fromisoformat(contact.peak_window_start)
        peak_window_end = datetime.fromisoformat(contact.peak_window_end)
        self.assertLessEqual(peak_window_start, exact_at)
        self.assertLessEqual(exact_at, peak_window_end)
        transit_timestamp = datetime.fromisoformat(response.technical_summary.transit_timestamp)
        if contact.phase == "applying":
            self.assertGreaterEqual(exact_at, transit_timestamp)
        elif contact.phase == "separating":
            self.assertLessEqual(exact_at, transit_timestamp)

    def test_natal_response_exposes_solar_return_and_block(self):
        profile = self.build_profile()
        response = NatalReadingService.build_response(NatalReadingRequest(profile=profile))

        self.assertEqual(response.status, "natal_calculated")
        self.assertIsNotNone(response.technical_summary.solar_return)
        self.assertIsNotNone(response.technical_summary.solar_return_chart_data)
        self.assertIsNotNone(response.technical_summary.year_map)
        self.assertGreaterEqual(len(response.technical_summary.topic_judgments), 6)
        self.assertEqual(response.technical_summary.solar_return.solar_year, 2026)
        self.assertEqual(response.technical_summary.solar_return.return_ascendant_sign, "Virgo")
        self.assertEqual(response.technical_summary.solar_return.sun_house, "House5")
        self.assertEqual(response.technical_summary.solar_return.year_lord_house, "House11")
        block_types = [block.block_type for block in response.interpretation_blocks]
        self.assertIn("solar_return", block_types)
        self.assertIn("year_map", block_types)
        topic_block = next(block for block in response.interpretation_blocks if block.block_type == "topic_judgment")
        self.assertTrue(topic_block.evidence_items)
        self.assertIsNotNone(topic_block.confidence)
        self.assertEqual(response.prediction_cards[0].title, "Current year map")
        self.assertEqual(response.prediction_cards[1].title, "How Fortune and Spirit divide the story")
        self.assertEqual(response.technical_summary.year_map.fortune_spirit_alignment, "split")
        self.assertTrue(response.technical_summary.year_map.annual_patterns)
        if response.technical_summary.year_map.fortune_spirit_axis is not None:
            self.assertIsInstance(response.technical_summary.year_map.fortune_spirit_axis, str)
        year_map_block = next(block for block in response.interpretation_blocks if block.block_type == "year_map")
        self.assertIn("natal", year_map_block.summary.lower())
        self.assertIn("solar return", year_map_block.summary.lower())

    def test_natal_response_includes_daily_horoscope(self):
        profile = self.build_profile()
        response = NatalReadingService.build_response(NatalReadingRequest(profile=profile))

        self.assertEqual(response.status, "natal_calculated")
        self.assertIsNotNone(response.daily_horoscope)
        self.assertEqual(response.daily_horoscope.title, "Daily horoscope")
        self.assertTrue(response.daily_horoscope.date)
        self.assertTrue(response.daily_horoscope.headline)
        self.assertTrue(response.daily_horoscope.main_transit)
        self.assertTrue(response.daily_horoscope.day_thesis)
        self.assertGreaterEqual(len(response.daily_horoscope.what_this_means), 3)
        self.assertGreaterEqual(len(response.daily_horoscope.why_the_chart_says_this), 2)
        self.assertTrue(response.daily_horoscope.larger_story)
        self.assertGreaterEqual(len(response.daily_horoscope.opportunities), 2)
        self.assertGreaterEqual(len(response.daily_horoscope.watch_fors), 2)
        self.assertTrue(response.daily_horoscope.best_move_primary)
        self.assertGreaterEqual(len(response.daily_horoscope.best_move_supporting), 2)
        self.assertTrue(response.daily_horoscope.timing)
        self.assertTrue(response.daily_horoscope.active_transits)
        self.assertGreaterEqual(len(response.daily_horoscope.action_checklist), 3)
        self.assertTrue(any("orb" in line.lower() for line in response.daily_horoscope.active_transits))
        self.assertTrue(any(contact.transit_body in response.daily_horoscope.headline for contact in response.technical_summary.transit_aspects[:1]))

    def test_topic_judgment_evidence_exposes_reasoning_metadata(self):
        profile = self.build_profile()
        response = NatalReadingService.build_response(NatalReadingRequest(profile=profile))

        first_topic = response.technical_summary.topic_judgments[0]
        first_evidence = first_topic.evidence_items[0]
        self.assertIn(first_evidence.polarity, {"support", "strain", "activation", "mixed"})
        self.assertIsNotNone(first_evidence.weight)
        self.assertGreaterEqual(first_evidence.weight, 1)
        self.assertIn(first_evidence.chart_context, {"natal", "annual_profection", "solar_return", "fortune_spirit", "transit"})
        self.assertIsNotNone(first_topic.synthesis)
        self.assertIsInstance(first_topic.supporting_evidence, list)
        self.assertIsInstance(first_topic.challenging_evidence, list)
        self.assertIsInstance(first_topic.activating_evidence, list)

    def test_synastry_unknown_time_uses_planetary_fallback(self):
        primary = self.build_profile(name="Person A")
        secondary = self.build_profile(name="Person B", birth_date="1981-05-10", birth_time="09:30", time_precision="unknown")
        response = SynastryReadingService.build_response(
            SynastryReadingRequest(primary_profile=primary, secondary_profile=secondary)
        )
        self.assertEqual(response.status, "synastry_planetary_fallback")
        self.assertTrue(response.technical_summary.inter_chart_aspects)
        self.assertEqual(response.technical_summary.engine_status, "planetary_longitudes_ready")
        self.assertEqual(response.technical_summary.precision_mode, "planetary_fallback")

    def test_synastry_exact_response_starts_from_natal_frames_and_yearly_activation(self):
        primary = self.build_profile(name="Person A")
        secondary = self.build_profile(
            name="Person B",
            birth_date="1981-01-10",
            birth_time="09:30",
        )
        response = SynastryReadingService.build_response(
            SynastryReadingRequest(primary_profile=primary, secondary_profile=secondary)
        )

        self.assertEqual(response.status, "synastry_calculated")
        self.assertIsNotNone(response.technical_summary.primary_annual_profection)
        self.assertIsNotNone(response.technical_summary.secondary_annual_profection)
        self.assertIsNotNone(response.technical_summary.primary_solar_return)
        self.assertIsNotNone(response.technical_summary.secondary_solar_return)
        self.assertGreaterEqual(len(response.technical_summary.topic_judgments), 5)
        block_types = [block.block_type for block in response.interpretation_blocks]
        self.assertEqual(block_types[:3], ["synastry_natal_frame", "synastry_natal_frame", "synastry_yearly_bridge"])
        self.assertEqual(block_types[3], "synastry_topic_judgment")
        self.assertIn("relationship_climate", block_types)
        topic_block = next(block for block in response.interpretation_blocks if block.block_type == "synastry_topic_judgment")
        self.assertEqual(topic_block.title, response.technical_summary.topic_judgments[0].title)
        self.assertTrue(topic_block.evidence_items)
        self.assertIsNotNone(topic_block.confidence)
        self.assertEqual(response.prediction_cards[0].title, "How the current years meet")
        self.assertEqual(response.prediction_cards[1].title, "What each person is bringing right now")
        self.assertEqual(response.prediction_cards[2].title, "Which relationship topic is carrying the bond")
        self.assertIn(response.technical_summary.topic_judgments[0].title.lower(), response.prediction_cards[2].summary.lower())
        topic_observations = [
            item.observation
            for topic in response.technical_summary.topic_judgments
            for item in topic.evidence_items
        ]
        self.assertTrue(any("Fortune" in observation or "Spirit" in observation for observation in topic_observations))
        self.assertTrue(any("witnesses Person" in observation or "presses Person" in observation for observation in topic_observations))
        self.assertIn("strongest repeated testimony", response.reading.oracle)

    def test_planetary_fallback_chart_suppresses_angles_and_houses(self):
        chart = NatalChartEngine.calculate_planetary_fallback_chart(
            birth_date="1979-01-01",
            birth_time="",
            utc_offset="-05:00",
        )
        self.assertEqual(chart.house_system, "Planetary-only fallback")
        self.assertFalse(chart.angles)
        self.assertFalse(chart.houses)
        self.assertTrue(chart.planets)
        self.assertTrue(all(planet.house is None for planet in chart.planets))
        self.assertIsNone(chart.traditional_context)
        self.assertTrue(all(planet.sect_status is None for planet in chart.planets))
        self.assertTrue(all(not planet.rules_houses for planet in chart.planets))

    def test_place_response_can_surface_ranked_candidates(self):
        request = PlaceResolveRequest(city="Detroit", country="USA", limit=2)
        best = SimpleNamespace(
            address="Detroit, Wayne County, Michigan, United States",
            latitude=42.3314,
            longitude=-83.0458,
            raw={
                "importance": 0.9,
                "type": "city",
                "address": {"city": "Detroit", "country": "United States"},
            },
        )
        alt = SimpleNamespace(
            address="Detroit Lakes, Becker County, Minnesota, United States",
            latitude=46.8172,
            longitude=-95.8453,
            raw={
                "importance": 0.95,
                "type": "city",
                "address": {"city": "Detroit Lakes", "country": "United States"},
            },
        )
        chosen, ranked = PlaceResolutionService._choose_candidate([alt, best], request)
        self.assertEqual(chosen.address, best.address)
        self.assertEqual([item.address for item in ranked[:2]], [best.address, alt.address])

    def test_place_scoring_prefers_exact_city_and_country(self):
        request = PlaceResolveRequest(city="Detroit", country="USA")
        best = SimpleNamespace(
            address="Detroit, Wayne County, Michigan, United States",
            raw={
                "importance": 0.9,
                "type": "city",
                "address": {"city": "Detroit", "country": "United States"},
            },
        )
        weaker = SimpleNamespace(
            address="Detroit Lakes, Becker County, Minnesota, United States",
            raw={
                "importance": 0.95,
                "type": "city",
                "address": {"city": "Detroit Lakes", "country": "United States"},
            },
        )
        chosen, ranked = PlaceResolutionService._choose_candidate([weaker, best], request)
        self.assertEqual(chosen.address, best.address)
        self.assertEqual(ranked[0].address, best.address)


if __name__ == "__main__":
    unittest.main()
