"""
Tests for the edit-command schema, the rule-based parser and the Gemini parser fallback.
Run:  python -m unittest tests.test_edit_engine
"""
import os
import unittest
from unittest import mock

from agents.edit_intent_parser import parse_edit_request
from agents.edit_rule_parser import ParseContext, parse_rules
from core.edit_schema import EditError, validate_command
from core.gemini_client import GeminiError


def rules(message: str, doc_type: str = "docx", **ctx) -> dict:
    result = parse_rules(message, ParseContext(doc_type=doc_type, **ctx))
    return {"commands": result.commands, "clarification": result.clarification}


class SchemaTests(unittest.TestCase):
    def test_valid_style_command_is_normalised(self):
        cmd = validate_command({"action": "update_style", "target": {"type": "title"},
                                "changes": {"font_family": "Arial", "font_size": 24.3, "color": "blue", "bold": True}}, "docx")
        self.assertEqual(cmd["changes"], {"font_family": "Arial", "font_size": 24.5, "color": "0070C0", "bold": True})

    def test_unknown_keys_are_dropped(self):
        cmd = validate_command({"action": "delete_slide", "target": {"type": "slide", "slide": 2}, "code": "rm -rf"}, "pptx")
        self.assertNotIn("code", cmd)

    def test_rejects_action_for_wrong_document_type(self):
        with self.assertRaises(EditError):
            validate_command({"action": "delete_slide", "target": {"type": "slide", "slide": 1}}, "docx")
        with self.assertRaises(EditError):
            validate_command({"action": "update_style", "document_type": "pptx", "target": {"type": "title"},
                              "changes": {"bold": True}}, "docx")

    def test_rejects_bad_values(self):
        bad = [
            {"action": "update_style", "target": {"type": "title"}, "changes": {"font_size": 9000}},
            {"action": "update_style", "target": {"type": "title"}, "changes": {"font_family": "Arial; drop"}},
            {"action": "update_style", "target": {"type": "title"}, "changes": {"color": "not-a-colour"}},
            {"action": "update_style", "target": {"type": "title"}, "changes": {}},
            {"action": "resize_image", "target": {"type": "logo"}, "scale": 50},
            {"action": "resize_image", "target": {"type": "title"}, "scale": 0.8},
            {"action": "insert_paragraph", "text": "x", "position": {"where": "after"}},
            {"action": "update_text", "target": {"type": "evil"}, "text": "x"},
            {"action": "replace_image", "target": {"type": "logo"}, "image_source": "C:/secret.png"},
            "not a dict",
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(EditError):
                validate_command(raw, "docx")


class RuleParserTests(unittest.TestCase):
    def test_required_docx_commands(self):
        cases = {
            "Change the document title font to Arial and make it bold.":
                [{"action": "update_style", "target": {"type": "title"}, "changes": {"font_family": "Arial", "bold": True}}],
            "Change the title font size to 24.":
                [{"action": "update_style", "target": {"type": "title"}, "changes": {"font_size": 24.0}}],
            "Change the title color to blue.":
                [{"action": "update_style", "target": {"type": "title"}, "changes": {"color": "blue"}}],
            "Remove the paragraph about enterprise architecture.":
                [{"action": "delete_paragraph", "target": {"type": "paragraph", "text": "enterprise architecture"}}],
            "Replace the company logo with the uploaded image.":
                [{"action": "replace_image", "target": {"type": "logo"}, "image_source": "last_upload"}],
            "Make the company logo 80% of its current size.":
                [{"action": "resize_image", "target": {"type": "logo"}, "scale": 0.8}],
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(rules(message)["commands"], expected)

    def test_insert_after_heading_keeps_payload(self):
        parsed = rules("Add this paragraph after the executive summary:\nOur platform helps enterprises automate document workflows.")
        self.assertEqual(parsed["commands"], [{
            "action": "insert_paragraph", "text": "Our platform helps enterprises automate document workflows.",
            "position": {"where": "after", "anchor": {"type": "heading", "text": "executive summary"}}}])

    def test_required_pptx_commands(self):
        cases = {
            "Change the title on slide 1 to Arial, 32 points.":
                {"action": "update_style", "target": {"type": "title", "slide": 1}, "changes": {"font_family": "Arial", "font_size": 32.0}},
            "Remove the third bullet from slide 2.": {"action": "delete_text", "target": {"type": "bullet", "index": 3, "slide": 2}},
            "Resize the logo on slide 1 to 80%.": {"action": "resize_image", "target": {"type": "logo", "slide": 1}, "scale": 0.8},
            "Move the logo slightly to the right.": {"action": "move_image", "target": {"type": "logo"}, "move": {"dx_inches": 0.25, "dy_inches": 0}},
            "Remove slide 5.": {"action": "delete_slide", "target": {"type": "slide", "slide": 5}},
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(rules(message, "pptx")["commands"], [expected])

    def test_ambiguous_requests_ask_instead_of_guessing(self):
        for message, doc_type in [("Change the font.", "docx"), ("Change the title color.", "pptx"),
                                  ("Resize the logo.", "pptx"), ("Add a bullet to slide 3.", "pptx"),
                                  ("Remove this paragraph.", "docx"), ("Move the logo slightly to the right.", "docx")]:
            with self.subTest(message=message):
                parsed = rules(message, doc_type)
                self.assertEqual(parsed["commands"], [])
                self.assertTrue(parsed["clarification"])

    def test_this_uses_the_selection_and_it_uses_the_previous_target(self):
        parsed = rules("Replace this sentence with: New text.", selection_kind="paragraph")
        self.assertEqual(parsed["commands"], [{"action": "update_text", "target": {"type": "selection"}, "text": "New text."}])
        parsed = rules("Now make it blue", last_target={"type": "title"})
        self.assertEqual(parsed["commands"][0]["target"], {"type": "title"})

    def test_compound_request_becomes_two_commands(self):
        commands = rules("Make the title blue and remove the paragraph about pricing")["commands"]
        self.assertEqual([c["action"] for c in commands], ["update_style", "delete_paragraph"])


class GeminiParserTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "EDIT_PARSER": "auto"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ctx = ParseContext(doc_type="docx", outline="¶1 [title] Acme")

    @mock.patch("agents.edit_intent_parser.ask_gemini_json")
    def test_valid_gemini_command_is_used(self, ask):
        ask.return_value = {"commands": [{"action": "update_style", "target": {"type": "title", "slide": None},
                                          "changes": {"italic": True, "bold": None}}], "clarification": None}
        result = parse_edit_request("italicise the heading at the top", self.ctx)
        self.assertEqual(result.parser, "gemini")
        self.assertEqual(result.commands, [{"action": "update_style", "target": {"type": "title"}, "changes": {"italic": True}}])

    @mock.patch("agents.edit_intent_parser.ask_gemini_json")
    def test_invalid_gemini_command_falls_back_to_rules(self, ask):
        ask.return_value = {"commands": [{"action": "run_python", "code": "import os"}]}
        result = parse_edit_request("Change the title color to blue.", self.ctx)
        self.assertEqual(result.parser, "rules")
        self.assertEqual(result.commands[0]["changes"], {"color": "blue"})
        self.assertIn("built-in parser", result.note)

    @mock.patch("agents.edit_intent_parser.ask_gemini_json", side_effect=GeminiError("HTTP 503"))
    def test_gemini_outage_falls_back_to_rules(self, _ask):
        result = parse_edit_request("Remove the paragraph about pricing", self.ctx)
        self.assertEqual(result.parser, "rules")
        self.assertEqual(result.commands[0]["action"], "delete_paragraph")

    @mock.patch("agents.edit_intent_parser.ask_gemini_json")
    def test_gemini_clarification_is_passed_on(self, ask):
        ask.return_value = {"commands": [], "clarification": "Which paragraph do you mean?"}
        result = parse_edit_request("tidy up that bit", self.ctx)
        self.assertEqual(result.clarification, "Which paragraph do you mean?")

    def test_without_api_key_rules_are_used(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            result = parse_edit_request("Change the title color to blue.", self.ctx)
        self.assertEqual(result.parser, "rules")


if __name__ == "__main__":
    unittest.main()
