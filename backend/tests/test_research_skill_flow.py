from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class ResearchSkillFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.original_fieldops_data_dir = os.environ.get("FIELDOPS_DATA_DIR")
        os.environ["FIELDOPS_DATA_DIR"] = self.tempdir.name
        self.addCleanup(self._restore_env)

        self.models = importlib.reload(importlib.import_module("models"))
        self.storage = importlib.reload(importlib.import_module("storage"))
        self.runner = importlib.reload(importlib.import_module("runner"))

        self.storage.ensure_state_file()

    def _restore_env(self) -> None:
        if self.original_fieldops_data_dir is None:
            os.environ.pop("FIELDOPS_DATA_DIR", None)
        else:
            os.environ["FIELDOPS_DATA_DIR"] = self.original_fieldops_data_dir

    def test_research_skill_classifies_explicit_action_type(self) -> None:
        mission = self.models.Mission(
            id="M-RESEARCH-CLASSIFY",
            title="Research heat pump incentives",
            agent="chuck",
            actionType="research_skill",
        )

        result = self.runner.classify_mission(mission)

        self.assertEqual(result["execution_type"], "action")
        self.assertEqual(result["action_type"], "research_skill")

    def test_research_skill_does_not_hijack_generate_word_report(self) -> None:
        mission = self.models.Mission(
            id="M-RESEARCH-COLLISION",
            title="Generate word report for weekly billing",
            agent="chuck",
            actionType="generate_word_report",
            objective="Generate word report from weekly billing notes.",
        )

        result = self.runner.classify_mission(mission)

        self.assertEqual(result["execution_type"], "action")
        self.assertEqual(result["action_type"], "generate_word_report")

    def test_research_skill_result_persists_expected_metadata(self) -> None:
        mission = self.models.Mission(
            id="M-RESEARCH-1",
            title="Research hemp seed oil conversion to diesel fuel",
            agent="chuck",
            missionClass="execution",
            sourceContext="fieldops_native",
            objective="Research whether hemp seed oil can be converted into diesel fuel at useful scale.",
            inputs="Scope: Montana and federal public sources\nMax Sources: 4",
            lane="l4",
            status="queued",
        )
        self.storage.save_state(self.models.AppState(missions=[mission], meta={"version": "test"}))

        fake_result = {
            "brief": "RESEARCH BRIEF: Hemp diesel\n\nEXECUTIVE SUMMARY:\nA useful first-pass result.",
            "summary": "A useful first-pass result.",
            "confidence": "MEDIUM",
            "findings": [
                "Multiple public sources describe transesterification as the core conversion pathway."
            ],
            "sources": [
                {
                    "url": "https://example.org/hemp-diesel",
                    "domain": "example.org",
                    "relevance_score": 0.82,
                    "excerpt": "Example excerpt",
                }
            ],
            "queries_run": ["hemp seed oil diesel fuel"],
            "source_count": 1,
        }

        with patch.object(self.runner, "run_research_skill", return_value=fake_result):
            state = self.storage.load_state()
            payload = self.runner.execute_mission(state.missions[0])
            self.storage.save_state(state)

        processed = self.storage.load_state().missions[0]
        self.assertEqual(payload["summary"], "A useful first-pass result.")
        self.assertEqual(processed.executionType, "action")
        self.assertEqual(processed.actionType, "research_skill")
        self.assertEqual(processed.actionStatus, "completed")
        self.assertEqual(processed.resultSummary, "A useful first-pass result.")
        self.assertEqual(processed.actionDetails["confidence"], "MEDIUM")
        self.assertEqual(processed.actionDetails["source_count"], 1)
        self.assertEqual(processed.actionDetails["queries_run"], ["hemp seed oil diesel fuel"])
        self.assertEqual(processed.actionDetails["sources"][0]["domain"], "example.org")


if __name__ == "__main__":
    unittest.main()
