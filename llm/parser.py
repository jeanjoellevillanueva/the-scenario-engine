import json
import logging
import re

from pydantic import ValidationError

from llm.schemas import AssessmentResult
from llm.schemas import LLMResponse

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when LLM response cannot be parsed."""

    pass


class LLMResponseParser:
    """Parses and validates structured JSON from LLM responses."""

    def parse(self, raw_content: str) -> LLMResponse:
        """Parse raw LLM response into structured LLMResponse."""
        json_str = self._extract_json(raw_content)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(
                'Failed to parse JSON from LLM response',
                extra={'error': str(e), 'content_preview': raw_content[:200]},
            )
            raise ParseError(f'Invalid JSON: {e}') from e

        try:
            return LLMResponse.model_validate(data)
        except ValidationError as e:
            logger.warning(
                'LLM response failed validation',
                extra={'errors': e.errors(), 'data': data},
            )
            raise ParseError(f'Validation failed: {e}') from e

    def parse_lenient(self, raw_content: str) -> LLMResponse:
        """Parse with fallback for malformed responses."""
        try:
            return self.parse(raw_content)
        except ParseError:
            logger.info('Using lenient parsing fallback')
            return self._fallback_parse(raw_content)

    def _extract_json(self, content: str) -> str:
        """Extract JSON from response, handling markdown code blocks."""
        content = content.strip()

        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            return json_match.group(1).strip()

        if content.startswith('{'):
            return content

        brace_start = content.find('{')
        if brace_start != -1:
            brace_count = 0
            for i, char in enumerate(content[brace_start:], start=brace_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return content[brace_start:i + 1]

        return content

    def _fallback_parse(self, raw_content: str) -> LLMResponse:
        """Create a minimal valid response when parsing fails."""
        message = raw_content.strip()

        json_match = re.search(r'"message"\s*:\s*"([^"]*)"', raw_content)
        if json_match:
            message = json_match.group(1)

        return LLMResponse(
            message=message,
            assessment=AssessmentResult(),
        )
