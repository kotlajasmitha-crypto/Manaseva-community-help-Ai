import io
import json
import urllib.error
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from app import (
    CATEGORIES,
    OLLAMA_MODEL,
    OllamaError,
    REPORT_CATEGORIES,
    UnsafeAIResponseError,
    ask_ollama,
    official_lookup_category,
    offline_demo_answer,
    requires_official_lookup,
    save_issue_report,
)


class OfflineDemoTests(unittest.TestCase):
    def test_offline_answers_cover_every_category_in_both_languages(self):
        for language in ("English", "తెలుగు"):
            for category in CATEGORIES:
                with self.subTest(language=language, category=category):
                    self.assertTrue(offline_demo_answer(category, language).strip())

    def test_health_demo_directs_emergencies_to_112_without_diagnosing(self):
        answer = offline_demo_answer("Health services", "English")
        self.assertIn("112", answer)
        self.assertIn("cannot diagnose", answer)

    def test_scheme_demo_points_to_official_verification(self):
        answer = offline_demo_answer("Government schemes", "English")
        self.assertIn("MyScheme", answer)
        self.assertIn("cannot confirm that you qualify", answer)


class IssueReportTests(unittest.TestCase):
    def test_report_is_saved_locally_with_only_the_submitted_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "reports.sqlite3"
            save_issue_report("Water shortage", "North ward", "Water supply stopped", db_path)
            with closing(sqlite3.connect(db_path)) as connection:
                row = connection.execute(
                    "SELECT category, location, description, created_at_utc FROM issue_reports"
                ).fetchone()

        self.assertEqual(row[:3], ("Water shortage", "North ward", "Water supply stopped"))
        self.assertTrue(row[3].endswith("+00:00"))

    def test_report_rejects_unknown_categories_and_blank_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "reports.sqlite3"
            for values in (
                ("Unknown", "North ward", "Issue"),
                (next(iter(REPORT_CATEGORIES)), " ", "Issue"),
                (next(iter(REPORT_CATEGORIES)), "North ward", "\n"),
            ):
                with self.subTest(values=values):
                    with self.assertRaises(ValueError):
                        save_issue_report(*values, db_path=db_path)

            self.assertFalse(db_path.exists())


class OllamaRequestTests(unittest.TestCase):
    def test_local_ai_error_is_explicit_when_service_is_unavailable(self):
        with patch(
            "app.urllib.request.urlopen",
            side_effect=urllib.error.URLError("not running"),
        ):
            with self.assertRaises(OllamaError) as caught:
                ask_ollama("Hello", "General help", "English")
        self.assertIn("Could not get a reply from local Ollama", str(caught.exception))

    def test_local_ai_reply_uses_selected_category_and_requested_language(self):
        response = io.BytesIO(
            json.dumps({"message": {"content": "Check the official scholarship portal."}}).encode()
        )
        with patch("app.urllib.request.urlopen", return_value=response) as open_url:
            answer = ask_ollama("Where can I apply?", "Education", "English")

        request = open_url.call_args.args[0]
        sent_messages = json.loads(request.data)["messages"]
        self.assertEqual(answer, "Check the official scholarship portal.")
        self.assertIn("Category: Education", sent_messages[-1]["content"])
        self.assertIn("simple English", sent_messages[0]["content"])
        self.assertEqual(json.loads(request.data)["model"], OLLAMA_MODEL)

    def test_unverified_links_and_phone_numbers_are_rejected(self):
        for content in (
            "Read more at https://not-a-verified-site.example.",
            "Open [this portal](relative-unverified-page).",
            "Call 9876543210 for assistance.",
        ):
            response = io.BytesIO(json.dumps({"message": {"content": content}}).encode())
            with self.subTest(content=content), patch(
                "app.urllib.request.urlopen", return_value=response
            ):
                with self.assertRaises(UnsafeAIResponseError):
                    ask_ollama("Need help", "General help", "English")

    def test_official_scheme_and_scholarship_questions_use_checked_guidance(self):
        self.assertTrue(requires_official_lookup("Can I qualify for a scholarship?", "Education"))
        self.assertTrue(requires_official_lookup("What scheme should I apply for?", "General help"))
        self.assertTrue(requires_official_lookup("ప్రభుత్వ పథకం అర్హత ఏమిటి?", "General help"))
        self.assertTrue(requires_official_lookup("Anything about this?", "Government schemes"))
        self.assertFalse(requires_official_lookup("Where is the nearest library?", "General help"))
        self.assertEqual(
            official_lookup_category("Where can I find official scholarship information?", "Health services"),
            "Education",
        )


if __name__ == "__main__":
    unittest.main()
