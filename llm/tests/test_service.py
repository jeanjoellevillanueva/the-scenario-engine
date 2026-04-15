from unittest.mock import MagicMock
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from learning_sessions.models import Message
from learning_sessions.models import Session

from llm.schemas import AssessmentResult
from llm.schemas import LLMClientResponse
from llm.schemas import LLMResponse
from llm.schemas import ObjectiveProgress
from llm.service import LLMService
from llm.service import LLMServiceError

from scenarios.models import LearningObjective
from scenarios.models import Scenario

User = get_user_model()


class TestLLMService(TestCase):
    """Tests for the LLM service."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            persona="You are Dave",
            setting="A farm",
            context="Cow is sick",
            is_active=True,
        )
        LearningObjective.objects.create(
            scenario=self.scenario,
            objective_id="LO1",
            description="Gather history",
            is_active=True,
        )
        self.session = Session.objects.create(
            scenario=self.scenario,
            learner=self.user,
            is_active=True,
        )

    def _create_mock_client(self, response_content):
        """Create a mock LLM client."""
        mock_client = MagicMock()
        mock_client.complete.return_value = LLMClientResponse(
            content=response_content,
            input_tokens=100,
            output_tokens=50,
            model="test-model",
            latency_ms=500,
        )
        return mock_client

    def test_process_message_saves_user_message(self):
        """process_message saves the user message."""
        response_json = '''
        {
            "message": "G'day!",
            "assessment": {
                "objectives_addressed": [],
                "objective_progress": {},
                "overall_score": 0,
                "scenario_state": "greeting",
                "flags": []
            }
        }
        '''
        mock_client = self._create_mock_client(response_json)
        service = LLMService(client=mock_client)

        service.process_message(self.session, "Hello Dave")

        user_messages = Message.objects.filter(
            session=self.session,
            role=Message.Role.USER,
        )
        assert user_messages.count() == 1
        assert user_messages.first().content == "Hello Dave"

    def test_process_message_saves_assistant_message(self):
        """process_message saves the assistant response."""
        response_json = '''
        {
            "message": "G'day mate!",
            "assessment": {
                "objectives_addressed": [],
                "objective_progress": {},
                "overall_score": 0,
                "scenario_state": "greeting",
                "flags": []
            }
        }
        '''
        mock_client = self._create_mock_client(response_json)
        service = LLMService(client=mock_client)

        assistant_msg, _ = service.process_message(self.session, "Hello")

        assert assistant_msg.role == Message.Role.ASSISTANT
        assert assistant_msg.content == "G'day mate!"

    def test_process_message_stores_assessment_metadata(self):
        """process_message stores assessment in message metadata."""
        response_json = '''
        {
            "message": "Response",
            "assessment": {
                "objectives_addressed": ["LO1"],
                "objective_progress": {
                    "LO1": {"status": "partial", "evidence": "Asked about symptoms"}
                },
                "overall_score": 2,
                "scenario_state": "history_gathering",
                "flags": ["student_uncertain"]
            }
        }
        '''
        mock_client = self._create_mock_client(response_json)
        service = LLMService(client=mock_client)

        assistant_msg, _ = service.process_message(self.session, "Hello")

        assert assistant_msg.assessment_metadata["objectives_addressed"] == ["LO1"]
        assert assistant_msg.assessment_metadata["overall_score"] == 2

    def test_process_message_updates_session_state(self):
        """process_message updates session assessment state."""
        response_json = '''
        {
            "message": "Response",
            "assessment": {
                "objectives_addressed": ["LO1"],
                "objective_progress": {
                    "LO1": {"status": "met", "evidence": "Complete history taken"}
                },
                "overall_score": 3,
                "scenario_state": "assessment",
                "flags": []
            }
        }
        '''
        mock_client = self._create_mock_client(response_json)
        service = LLMService(client=mock_client)

        service.process_message(self.session, "Hello")
        self.session.refresh_from_db()

        assert self.session.assessment_state["latest_score"] == 3
        assert self.session.assessment_state["scenario_state"] == "assessment"
        assert "LO1" in self.session.assessment_state["objective_progress"]

    def test_process_message_returns_parsed_response(self):
        """process_message returns the parsed LLM response."""
        response_json = '''
        {
            "message": "Test response",
            "assessment": {
                "objectives_addressed": ["LO1"],
                "objective_progress": {},
                "overall_score": 1,
                "scenario_state": "test",
                "flags": []
            }
        }
        '''
        mock_client = self._create_mock_client(response_json)
        service = LLMService(client=mock_client)

        _, llm_response = service.process_message(self.session, "Hello")

        assert isinstance(llm_response, LLMResponse)
        assert llm_response.message == "Test response"
        assert llm_response.assessment.overall_score == 1

    def test_process_message_handles_client_error(self):
        """process_message raises LLMServiceError on client failure."""
        mock_client = MagicMock()
        mock_client.complete.side_effect = Exception("API Error")
        service = LLMService(client=mock_client)

        with self.assertRaises(LLMServiceError):
            service.process_message(self.session, "Hello")

    def test_process_message_uses_lenient_parse_on_failure(self):
        """process_message falls back to lenient parsing."""
        malformed_response = '''
        {
            "message": "Fallback message",
            "assessment_broken
        '''
        mock_client = self._create_mock_client(malformed_response)
        service = LLMService(client=mock_client)

        _, llm_response = service.process_message(self.session, "Hello")

        assert "Fallback message" in llm_response.message

    def test_process_message_increments_sequence(self):
        """process_message correctly sequences messages."""
        response_json = '''
        {
            "message": "Response",
            "assessment": {
                "objectives_addressed": [],
                "objective_progress": {},
                "overall_score": 0,
                "scenario_state": "test",
                "flags": []
            }
        }
        '''
        mock_client = self._create_mock_client(response_json)
        service = LLMService(client=mock_client)

        service.process_message(self.session, "First")
        service.process_message(self.session, "Second")

        messages = Message.objects.filter(session=self.session).order_by("sequence")
        sequences = [m.sequence for m in messages]

        assert sequences == [1, 2, 3, 4]
