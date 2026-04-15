from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class GmailMissionFlowTests(unittest.TestCase):
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

    def test_gmail_draft_mission_persists_across_waiting_and_complete(self) -> None:
        mission = self.models.Mission(
            id="M-GMAIL-1",
            title="Draft partner follow-up",
            agent="chuck",
            missionClass="execution",
            sourceContext="fieldops_native",
            objective="Create a Gmail draft for a partner follow-up.",
            inputs=(
                "To: partner@example.com\n"
                "Cc: manager@example.com\n"
                "Subject: FieldOps status update\n"
                "Body: Thanks for the call. Here is the current status update."
            ),
            expectedOutput="Return: Gmail draft metadata and saved draft confirmation.",
            priority="high",
            lane="l2",
            status="queued",
        )
        self.storage.save_state(self.models.AppState(missions=[mission], meta={"version": "test"}))

        with patch.object(
            self.runner,
            "create_gmail_draft",
            return_value={"draft_id": "draft-123", "message_id": "msg-456"},
        ):
            state = self.storage.load_state()
            result_payload = self.runner.execute_mission(state.missions[0])
            self.storage.save_state(state)

        processed_state = self.storage.load_state()
        self.assertEqual(len(processed_state.missions), 1)
        waiting = processed_state.missions[0]

        self.assertEqual(result_payload["summary"], "Gmail draft created successfully")
        self.assertEqual(waiting.status, "waiting")
        self.assertEqual(waiting.executionType, "action")
        self.assertEqual(waiting.actionType, "gmail_create_draft")
        self.assertEqual(waiting.actionStatus, "completed")
        self.assertEqual(waiting.resultSummary, "Gmail draft created successfully")
        self.assertEqual(waiting.actionDetails["draft_id"], "draft-123")
        self.assertEqual(waiting.actionDetails["message_id"], "msg-456")
        self.assertEqual(waiting.actionDetails["subject"], "FieldOps status update")
        self.assertEqual(waiting.actionDetails["to"], "partner@example.com")
        self.assertEqual(waiting.actionDetails["cc"], "manager@example.com")

        completed = waiting.model_copy(deep=True)
        completed.status = "complete"
        completed.completedAt = datetime.now()

        processed_state.missions = []
        processed_state.completedMissions = [completed]
        self.storage.save_state(processed_state)

        reloaded_state = self.storage.load_state()
        self.assertEqual(len(reloaded_state.missions), 0)
        self.assertEqual(len(reloaded_state.completedMissions), 1)

        persisted = reloaded_state.completedMissions[0]
        self.assertEqual(persisted.status, "complete")
        self.assertEqual(persisted.actionType, "gmail_create_draft")
        self.assertEqual(persisted.actionStatus, "completed")
        self.assertEqual(persisted.actionDetails["draft_id"], "draft-123")
        self.assertEqual(persisted.actionDetails["message_id"], "msg-456")
        self.assertEqual(persisted.actionDetails["subject"], "FieldOps status update")
        self.assertEqual(persisted.mockResult["action_details"]["draft_id"], "draft-123")

    def test_gmail_field_extraction_keeps_blank_headers_empty(self) -> None:
        mission = self.models.Mission(
            id="M-GMAIL-2",
            title="Draft test email",
            agent="chuck",
            inputs=(
                "To: guyl@ncat.org\n"
                "CC:\n"
                "BCC:\n"
                "Subject: test\n"
                "Body: test"
            ),
        )

        fields = self.runner._extract_gmail_draft_fields(mission)

        self.assertEqual(fields["to"], "guyl@ncat.org")
        self.assertEqual(fields["cc"], "")
        self.assertEqual(fields["bcc"], "")
        self.assertEqual(fields["subject"], "test")
        self.assertEqual(fields["body"], "test")

    def test_gmail_body_does_not_absorb_expected_output_text(self) -> None:
        mission = self.models.Mission(
            id="M-GMAIL-3",
            title="Draft multiline email",
            agent="chuck",
            inputs=(
                "To: guyl@ncat.org\n"
                "Subject: FieldOps update\n"
                "Body: First line.\n"
                "Second line.\n"
                "Expected Output: A real Gmail draft should be created."
            ),
            expectedOutput="A real Gmail draft should be created.",
        )

        fields = self.runner._extract_gmail_draft_fields(mission)

        self.assertEqual(fields["body"], "First line.\nSecond line.")


if __name__ == "__main__":
    unittest.main()
