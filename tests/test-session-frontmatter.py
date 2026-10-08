#!/usr/bin/env python3
"""Round-trip session metadata without requiring a model or a user profile."""

import json
from pathlib import Path
import runpy
import unittest


HELPER = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/llm-wiki-session"))


class SessionFrontmatterTests(unittest.TestCase):
    def test_scalars_survive_repeated_round_trips(self):
        for text in (
            "中文摘要",
            "회선상세 성능탭",
            "Research 📝",
            'A "quoted" summary\nwith a C:\\Users\\wiki path',
            "",
            "true",
            "123",
            "null",
        ):
            with self.subTest(text=text):
                encoded = HELPER["yaml_string"](text)
                self.assertEqual(json.dumps(text, ensure_ascii=False), encoded)
                for _ in range(3):
                    fields, body = HELPER["split_frontmatter"](
                        f"---\nsummary: {encoded}\n---\nBody\n"
                    )
                    self.assertEqual(text, fields["summary"])
                    self.assertEqual("Body\n", body)
                    self.assertEqual(encoded, HELPER["yaml_string"](fields["summary"]))

    def test_legacy_ascii_escaped_scalars_are_decoded(self):
        summary = '中文 "quoted" C:\\Users\\wiki'
        fields, _ = HELPER["split_frontmatter"](
            f"---\nsummary: {json.dumps(summary)}\n---\nBody\n"
        )
        self.assertEqual(summary, fields["summary"])

    def test_plain_and_non_json_scalars_remain_compatible(self):
        fields, _ = HELPER["split_frontmatter"](
            '---\ntype: notes\nsummary: "C:\\Users\\wiki"\ntopics: ["demo"]\n---\n'
        )
        self.assertEqual("notes", fields["type"])
        self.assertEqual("C:\\Users\\wiki", fields["summary"])
        self.assertEqual(["demo"], fields["topics"])


if __name__ == "__main__":
    unittest.main()
