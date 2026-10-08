#!/usr/bin/env python3
"""Exercise session and feedback promotion with synthetic multiline content."""

import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/llm-wiki-session"
HELPER = runpy.run_path(str(SCRIPT))


class SessionPromotionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.hub = Path(self.temporary.name) / "wiki"
        self.topic = self.hub / "topics/demo"
        (self.topic / "raw/notes").mkdir(parents=True)
        (self.topic / "log.md").write_text("# Log\n", encoding="utf-8")
        (self.hub / "wikis.json").write_text(
            json.dumps({"wikis": {"demo": {"path": "topics/demo"}}}), encoding="utf-8"
        )

    def cli(self, *args):
        return subprocess.check_output(
            [sys.executable, str(SCRIPT), "--hub", str(self.hub), *args],
            text=True, cwd=self.hub,
        ).strip()

    def test_session_promotion_has_frontmatter_and_preserves_digest_body(self):
        digest = Path(self.cli("capture", "--harness", "manual", "--session-id", "sample",
                               "--summary", "Synthetic summary"))
        _, original_body = HELPER["split_frontmatter"](digest.read_text(encoding="utf-8"))
        note = Path(self.cli("promote", "manual:sample", "--topic", "demo"))
        text = note.read_text(encoding="utf-8")
        fields, body = HELPER["split_frontmatter"](text)
        self.assertEqual("notes", fields.get("type"))
        self.assertEqual("Synthetic summary", fields["summary"])
        self.assertTrue(body.startswith("\n# Session Digest Promotion: manual:sample\n"))
        self.assertTrue(text.endswith(original_body.strip() + "\n"))

    def test_feedback_promotion_quotes_every_preview_line(self):
        candidate = {
            "id": "synthetic-feedback", "feedback_type": "correction",
            "distilled_lesson": "First lesson.\n\nSecond lesson.",
            "text_preview": "First preview line.\n\nSecond preview line.",
            "confidence": "high", "harness": "manual",
        }
        path = self.hub / ".sessions/feedback/candidates.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(candidate) + "\n", encoding="utf-8")
        note = Path(self.cli("feedback", "promote", candidate["id"], "--topic", "demo"))
        fields, body = HELPER["split_frontmatter"](note.read_text(encoding="utf-8"))
        self.assertEqual("notes", fields.get("type"))
        self.assertIn("\n## Distilled Lesson\n\nFirst lesson.\n\nSecond lesson.\n", body)
        self.assertIn("\n> First preview line.\n> \n> Second preview line.\n", body)
        self.assertIn("\n| Feedback type | correction |\n", body)
        self.assertIn("\n## Usage Guidance\n", body)


if __name__ == "__main__":
    unittest.main()
