import pytest

from llm.parser import LLMResponseParser
from llm.parser import ParseError


class TestLLMResponseParser:
    """Tests for the LLM response parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = LLMResponseParser()

    def test_parse_valid_json(self):
        """Parser correctly extracts valid JSON response."""
        raw_content = '''
        {
            "message": "G'day mate, Duchess has been off her tucker since Tuesday.",
            "assessment": {
                "objectives_addressed": ["LO1"],
                "objective_progress": {
                    "LO1": {"status": "partial", "evidence": "Asked about symptoms"}
                },
                "overall_score": 1,
                "scenario_state": "history_gathering",
                "flags": []
            }
        }
        '''
        result = self.parser.parse(raw_content)

        assert result.message == "G'day mate, Duchess has been off her tucker since Tuesday."
        assert result.assessment.objectives_addressed == ["LO1"]
        assert result.assessment.objective_progress["LO1"].status == "partial"
        assert result.assessment.overall_score == 1

    def test_parse_json_in_markdown_code_block(self):
        """Parser extracts JSON from markdown code blocks."""
        raw_content = '''
        ```json
        {
            "message": "Hello there!",
            "assessment": {
                "objectives_addressed": [],
                "objective_progress": {},
                "overall_score": 0,
                "scenario_state": "greeting",
                "flags": []
            }
        }
        ```
        '''
        result = self.parser.parse(raw_content)

        assert result.message == "Hello there!"
        assert result.assessment.scenario_state == "greeting"

    def test_parse_json_with_prefix_text(self):
        """Parser extracts JSON even with prefix text."""
        raw_content = '''
        Here is my response:
        {
            "message": "Test message",
            "assessment": {
                "objectives_addressed": [],
                "objective_progress": {},
                "overall_score": 0,
                "scenario_state": "unknown",
                "flags": []
            }
        }
        '''
        result = self.parser.parse(raw_content)

        assert result.message == "Test message"

    def test_parse_invalid_json_raises_error(self):
        """Parser raises ParseError for invalid JSON."""
        raw_content = "This is not valid JSON at all"

        with pytest.raises(ParseError):
            self.parser.parse(raw_content)

    def test_parse_missing_required_field_raises_error(self):
        """Parser raises ParseError when required fields are missing."""
        raw_content = '{"assessment": {}}'

        with pytest.raises(ParseError):
            self.parser.parse(raw_content)

    def test_parse_lenient_fallback_for_malformed_response(self):
        """Lenient parser returns fallback for malformed responses."""
        raw_content = "Just a plain text response without JSON"

        result = self.parser.parse_lenient(raw_content)

        assert result.message == raw_content.strip()
        assert result.assessment.overall_score == 0

    def test_parse_lenient_extracts_message_from_partial_json(self):
        """Lenient parser extracts message from partial JSON."""
        raw_content = '''
        {
            "message": "Extracted message",
            "invalid_json_here
        '''
        result = self.parser.parse_lenient(raw_content)

        assert result.message == "Extracted message"

    def test_parse_validates_score_range(self):
        """Parser validates overall_score is within range."""
        raw_content = '''
        {
            "message": "Test",
            "assessment": {
                "objectives_addressed": [],
                "objective_progress": {},
                "overall_score": 10,
                "scenario_state": "test",
                "flags": []
            }
        }
        '''
        with pytest.raises(ParseError):
            self.parser.parse(raw_content)

    def test_parse_validates_status_values(self):
        """Parser validates objective status values."""
        raw_content = '''
        {
            "message": "Test",
            "assessment": {
                "objectives_addressed": [],
                "objective_progress": {
                    "LO1": {"status": "invalid_status", "evidence": null}
                },
                "overall_score": 0,
                "scenario_state": "test",
                "flags": []
            }
        }
        '''
        with pytest.raises(ParseError):
            self.parser.parse(raw_content)
