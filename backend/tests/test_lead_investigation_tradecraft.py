from __future__ import annotations

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from lead_investigation import (  # noqa: E402
    SearchResult,
    _pick_relevant_links,
    _score_search_result_for_homepage,
    _score_search_result_for_investigation,
)


class LeadInvestigationTradecraftTests(unittest.TestCase):
    def test_retail_investigation_prefers_local_press_operator_signal(self) -> None:
        local_press = SearchResult(
            url="https://dailyinterlake.com/news/2024/jan/10/take-5-oil-change-opens-kalispell-last-best-oil-change-llc/",
            title="Take 5 Oil Change opens in Kalispell under Last Best Oil Change LLC",
            snippet="Ryan Schneider, franchise manager for Last Best Oil Change LLC, said the Montana rollout is expanding.",
            source_type="local_press",
        )
        generic_locations = SearchResult(
            url="https://www.take5.com/locations/",
            title="Find a Take 5 Oil Change Location Near You!",
            snippet="Visit a Take 5 near you for oil changes and vehicle maintenance.",
            source_type="company_website",
        )

        press_score = _score_search_result_for_investigation(
            local_press,
            target_name="Take 5 Oil Change",
            city_state="Butte, Montana",
            lead_context="Identify the decision maker for outreach",
            profile_key="retail_multi_site",
        )
        generic_score = _score_search_result_for_investigation(
            generic_locations,
            target_name="Take 5 Oil Change",
            city_state="Butte, Montana",
            lead_context="Identify the decision maker for outreach",
            profile_key="retail_multi_site",
        )

        self.assertGreater(press_score, generic_score)

    def test_retail_homepage_discovery_penalizes_generic_locations_index(self) -> None:
        local_press = SearchResult(
            url="https://dailyinterlake.com/news/2024/jan/10/take-5-oil-change-opens-kalispell-last-best-oil-change-llc/",
            title="Take 5 grand opening led by Last Best Oil Change LLC",
            snippet="Ryan Schneider, franchise manager, is leading the operator rollout in Montana.",
            source_type="local_press",
        )
        generic_locations = SearchResult(
            url="https://www.take5.com/locations/",
            title="Find a Take 5 Oil Change Location Near You!",
            snippet="Find a Take 5 near you.",
            source_type="company_website",
        )

        press_score = _score_search_result_for_homepage(
            local_press,
            "Take 5 Oil Change",
            "",
            "Butte, Montana",
            "retail_multi_site",
        )
        generic_score = _score_search_result_for_homepage(
            generic_locations,
            "Take 5 Oil Change",
            "",
            "Butte, Montana",
            "retail_multi_site",
        )

        self.assertGreater(press_score, generic_score)

    def test_generic_brand_locations_page_does_not_follow_unrelated_states(self) -> None:
        links = [
            "https://www.take5.com/about/",
            "https://www.take5.com/contact/",
            "https://www.take5.com/locations/alabama/birmingham/",
            "https://www.take5.com/locations/montana/butte/",
        ]

        chosen = _pick_relevant_links(
            "https://www.take5.com/locations/",
            links,
            "retail_multi_site",
            "Butte, Montana",
        )

        self.assertIn("https://www.take5.com/about/", chosen)
        self.assertIn("https://www.take5.com/contact/", chosen)
        self.assertIn("https://www.take5.com/locations/montana/butte/", chosen)
        self.assertNotIn("https://www.take5.com/locations/alabama/birmingham/", chosen)


if __name__ == "__main__":
    unittest.main()
