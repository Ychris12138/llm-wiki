#!/usr/bin/env python3
"""Check promotion records across real CLI promotions and later captures."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/llm-wiki-session"


class PromotionRecordTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.hub = Path(self.temporary.name) / "wiki"
        for topic in ("first", "second"):
            (self.hub / "topics" / topic / "raw/notes").mkdir(parents=True)
        (self.hub / "wikis.json").write_text('{"wikis": {}}', encoding="utf-8")
        self.digest = self.capture()
        self.state_path = self.hub / ".sessions/state/manual/sample.json"

    def cli(self, *args):
        return subprocess.check_output(
            [sys.executable, str(SCRIPT), "--hub", str(self.hub), *args],
            text=True, cwd=self.hub,
        ).strip()

    def capture(self):
        return Path(self.cli("capture", "--harness", "manual", "--session-id", "sample",
                             "--summary", "Synthetic summary"))

    def assert_records(self, expected):
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        header = self.digest.read_text(encoding="utf-8").split("\n---\n", 1)[0]
        match = re.search(r"^promoted_to: (.*)$", header, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(sorted(expected), json.loads(match.group(1)))
        self.assertEqual(sorted(expected), state["promoted_to"])

    def test_promotion_updates_digest_without_rewriting_other_content(self):
        original = self.digest.read_text(encoding="utf-8")
        original += "\n## Local annotation\n\npromoted_to: body text must stay unchanged\n"
        self.digest.write_text(original, encoding="utf-8")
        destination = self.cli("promote", "manual:sample", "--topic", "first")
        self.assert_records([destination])
        updated = self.digest.read_text(encoding="utf-8")
        self.assertEqual(original, re.sub(
            r"^promoted_to: .*", "promoted_to: []", updated, count=1, flags=re.MULTILINE
        ))

    def test_recapture_preserves_records_and_repeated_promotions_are_unique(self):
        first = self.cli("promote", "manual:sample", "--topic", "first")
        self.digest = self.capture()
        self.assert_records([first])
        second = self.cli("promote", "manual:sample", "--topic", "second")
        self.cli("promote", "manual:sample", "--topic", "first", "--force")
        self.assert_records([first, second])
        self.digest = self.capture()
        self.assert_records([first, second])

    def test_missing_header_field_is_restored_and_backslashes_are_preserved(self):
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        previous = r"C:\Users\someone\wiki\raw\notes\previous.md"
        state["promoted_to"] = [previous]
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        original = self.digest.read_text(encoding="utf-8").replace("promoted_to: []\n", "", 1)
        original += "\npromoted_to: this is a body annotation\n"
        self.digest.write_text(original, encoding="utf-8")
        destination = self.cli("promote", "manual:sample", "--topic", "first")
        self.assert_records([previous, destination])
        updated_body = self.digest.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        self.assertEqual(original.split("\n---\n", 1)[1], updated_body)


if __name__ == "__main__":
    unittest.main()
