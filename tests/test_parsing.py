"""
tests/test_parsing.py
Unit tests for the pure utility functions in utils/files.py and utils/guide.py.
Run with:  pytest tests/test_parsing.py -v
"""
import json
import sys
import types as _types
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Minimal stubs so the modules can be imported without Streamlit or google-genai
# ---------------------------------------------------------------------------

# Stub streamlit
st_stub = MagicMock()
sys.modules.setdefault("streamlit", st_stub)

# Stub google.genai and google.genai.types
google_stub = _types.ModuleType("google")
genai_stub = _types.ModuleType("google.genai")
genai_types_stub = _types.ModuleType("google.genai.types")
genai_types_stub.Part = MagicMock()
google_stub.genai = genai_stub
genai_stub.types = genai_types_stub
sys.modules.setdefault("google", google_stub)
sys.modules.setdefault("google.genai", genai_stub)
sys.modules.setdefault("google.genai.types", genai_types_stub)

# Stub heavy native libs
for mod in ("fitz", "pptx", "pptx.util"):
    sys.modules.setdefault(mod, MagicMock())

# Now safe to import
from utils.files import clean_to_markdown, parse_json_response  # noqa: E402
from utils.guide import split_topics, topic_from_lines          # noqa: E402


# ---------------------------------------------------------------------------
# clean_to_markdown
# ---------------------------------------------------------------------------

class TestCleanToMarkdown(unittest.TestCase):

    def test_empty_string_returns_empty(self):
        self.assertEqual(clean_to_markdown(""), "")

    def test_none_like_falsy_returns_empty(self):
        # Function guards on `if not raw_text`
        self.assertEqual(clean_to_markdown(""), "")

    def test_collapses_multiple_blank_lines(self):
        result = clean_to_markdown("line1\n\n\n\n\nline2")
        self.assertNotIn("\n\n\n", result)

    def test_normalises_crlf(self):
        result = clean_to_markdown("line1\r\nline2\r\nline3")
        self.assertNotIn("\r", result)
        self.assertIn("line1", result)
        self.assertIn("line2", result)

    def test_collapses_inline_spaces(self):
        result = clean_to_markdown("word1    word2\t\tword3")
        self.assertNotIn("  ", result)

    def test_slide_heading_promoted(self):
        result = clean_to_markdown("Slide 3: Overview")
        self.assertTrue(result.startswith("## "), f"Expected heading, got: {result!r}")

    def test_chapter_heading_promoted(self):
        result = clean_to_markdown("Chapter 5 Introduction")
        self.assertIn("##", result)

    def test_normal_sentence_not_promoted(self):
        sentence = "This is a normal sentence that should not be a heading."
        result = clean_to_markdown(sentence)
        self.assertNotIn("##", result)

    def test_strips_leading_trailing_whitespace(self):
        result = clean_to_markdown("   hello world   ")
        self.assertEqual(result, "hello world")

    def test_preserves_content(self):
        text = "Important concept: binary trees store values hierarchically."
        result = clean_to_markdown(text)
        self.assertIn("binary trees", result)


# ---------------------------------------------------------------------------
# parse_json_response
# ---------------------------------------------------------------------------

class TestParseJsonResponse(unittest.TestCase):

    def test_plain_json_object(self):
        raw = '{"questions": [{"q": "test"}]}'
        result = parse_json_response(raw)
        self.assertIn("questions", result)
        self.assertEqual(result["questions"][0]["q"], "test")

    def test_strips_json_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        result = parse_json_response(raw)
        self.assertEqual(result["key"], "value")

    def test_strips_plain_fence(self):
        raw = '```\n{"key": "value"}\n```'
        result = parse_json_response(raw)
        self.assertEqual(result["key"], "value")

    def test_handles_whitespace_padding(self):
        raw = '  \n  {"a": 1}  \n  '
        result = parse_json_response(raw)
        self.assertEqual(result["a"], 1)

    def test_invalid_json_raises(self):
        with self.assertRaises(json.JSONDecodeError):
            parse_json_response("this is not json")

    def test_nested_structure_preserved(self):
        payload = {"questions": [{"answer_index": 2, "choices": ["A", "B", "C", "D"]}]}
        raw = json.dumps(payload)
        result = parse_json_response(raw)
        self.assertEqual(result["questions"][0]["answer_index"], 2)
        self.assertEqual(len(result["questions"][0]["choices"]), 4)


# ---------------------------------------------------------------------------
# topic_from_lines
# ---------------------------------------------------------------------------

class TestTopicFromLines(unittest.TestCase):

    def _make_lines(self, body_text: str) -> list[str]:
        return body_text.splitlines()

    def test_extracts_answer_section(self):
        lines = self._make_lines(
            "**THE RULE**: Some rule.\n"
            "**THE CHALLENGE**: A problem.\n"
            "**[ANSWER]**: The answer here."
        )
        result = topic_from_lines("My Topic", lines)
        self.assertEqual(result["title"], "My Topic")
        self.assertIn("The answer here", result["answer"])
        self.assertNotIn("[ANSWER]", result["body"])

    def test_missing_answer_section_returns_placeholder(self):
        lines = self._make_lines("Just some body text with no answer section.")
        result = topic_from_lines("No Answer", lines)
        self.assertEqual(result["answer"], "_No answer section returned._")

    def test_body_does_not_include_answer(self):
        lines = self._make_lines(
            "Body content here.\n**[ANSWER]**: Answer content here."
        )
        result = topic_from_lines("T", lines)
        self.assertNotIn("Answer content here", result["body"])
        self.assertIn("Answer content here", result["answer"])

    def test_case_insensitive_answer_marker(self):
        lines = self._make_lines("Body.\n**[answer]**: lowercase marker answer.")
        result = topic_from_lines("T", lines)
        self.assertIn("lowercase marker answer", result["answer"])


# ---------------------------------------------------------------------------
# split_topics
# ---------------------------------------------------------------------------

class TestSplitTopics(unittest.TestCase):

    def test_single_topic(self):
        md = "## Topic One\nSome content.\n**[ANSWER]**: Answer."
        topics = split_topics(md)
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]["title"], "Topic One")

    def test_multiple_topics(self):
        md = (
            "## Topic One\nContent one.\n**[ANSWER]**: Answer one.\n\n"
            "## Topic Two\nContent two.\n**[ANSWER]**: Answer two."
        )
        topics = split_topics(md)
        self.assertEqual(len(topics), 2)
        self.assertEqual(topics[0]["title"], "Topic One")
        self.assertEqual(topics[1]["title"], "Topic Two")

    def test_no_headings_returns_empty(self):
        md = "Just plain text with no ## headings at all."
        topics = split_topics(md)
        self.assertEqual(topics, [])

    def test_empty_string_returns_empty(self):
        self.assertEqual(split_topics(""), [])

    def test_topic_content_isolated(self):
        md = "## Alpha\nAlpha body.\n**[ANSWER]**: Alpha answer.\n## Beta\nBeta body."
        topics = split_topics(md)
        self.assertNotIn("Beta", topics[0]["body"])
        self.assertNotIn("Alpha", topics[1]["body"])

    def test_title_stripped_of_whitespace(self):
        md = "##   Padded Title   \nContent."
        topics = split_topics(md)
        self.assertEqual(topics[0]["title"], "Padded Title")


if __name__ == "__main__":
    unittest.main()
