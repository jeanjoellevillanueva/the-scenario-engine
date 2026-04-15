from unittest.mock import MagicMock
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from learning_sessions.models import Message
from learning_sessions.models import Session

from llm.schemas import AssessmentResult
from llm.schemas import LLMResponse

from scenarios.models import LearningObjective
from scenarios.models import Scenario

User = get_user_model()


class TestSessionAPI(APITestCase):
    """Tests for the session API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
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
        self.client.force_authenticate(user=self.user)

    def test_create_session_success(self):
        """Creating a session returns 201 and session data."""
        url = reverse("learning_sessions:session_list_create")
        data = {"scenario": str(self.scenario.id)}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert response.data["scenario"] == str(self.scenario.id)
        assert response.data["status"] == "in_progress"

    def test_create_session_assigns_current_user(self):
        """Session is assigned to the authenticated user."""
        url = reverse("learning_sessions:session_list_create")
        data = {"scenario": str(self.scenario.id)}

        response = self.client.post(url, data, format="json")

        session = Session.objects.get(id=response.data["id"])
        assert session.learner == self.user

    def test_create_session_requires_auth(self):
        """Creating a session requires authentication."""
        self.client.force_authenticate(user=None)
        url = reverse("learning_sessions:session_list_create")
        data = {"scenario": str(self.scenario.id)}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_sessions_returns_user_sessions_only(self):
        """Listing sessions returns only the current user's sessions."""
        user_session = Session.objects.create(
            scenario=self.scenario,
            learner=self.user,
            is_active=True,
        )
        other_session = Session.objects.create(
            scenario=self.scenario,
            learner=self.other_user,
            is_active=True,
        )
        url = reverse("learning_sessions:session_list_create")

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        session_ids = [s["id"] for s in response.data]
        assert str(user_session.id) in session_ids
        assert str(other_session.id) not in session_ids

    def test_get_session_detail_success(self):
        """Getting session detail returns full session data."""
        session = Session.objects.create(
            scenario=self.scenario,
            learner=self.user,
            is_active=True,
        )
        url = reverse(
            "learning_sessions:session_detail",
            kwargs={"session_id": session.id},
        )

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(session.id)
        assert "scenario_detail" in response.data
        assert "messages" in response.data

    def test_get_session_detail_forbidden_for_other_user(self):
        """Cannot access another user's session."""
        other_session = Session.objects.create(
            scenario=self.scenario,
            learner=self.other_user,
            is_active=True,
        )
        url = reverse(
            "learning_sessions:session_detail",
            kwargs={"session_id": other_session.id},
        )

        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMessageAPI(APITestCase):
    """Tests for the message API endpoints."""

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
        self.client.force_authenticate(user=self.user)

    @patch("learning_sessions.views.LLMService")
    def test_send_message_success(self, mock_service_class):
        """Sending a message returns 201 with assistant response."""
        mock_service = MagicMock()
        mock_message = Message(
            session=self.session,
            role=Message.Role.ASSISTANT,
            content="G'day mate!",
            sequence=2,
            assessment_metadata={},
        )
        mock_response = LLMResponse(
            message="G'day mate!",
            assessment=AssessmentResult(),
        )
        mock_service.process_message.return_value = (mock_message, mock_response)
        mock_service_class.return_value = mock_service

        url = reverse(
            "learning_sessions:session_messages",
            kwargs={"session_id": self.session.id},
        )
        data = {"content": "Hello Dave"}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "message" in response.data
        assert "assessment" in response.data
        assert response.data["message"]["content"] == "G'day mate!"

    def test_send_message_requires_content(self):
        """Sending a message requires content field."""
        url = reverse(
            "learning_sessions:session_messages",
            kwargs={"session_id": self.session.id},
        )
        data = {}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_message_validates_content_length(self):
        """Content must not be empty."""
        url = reverse(
            "learning_sessions:session_messages",
            kwargs={"session_id": self.session.id},
        )
        data = {"content": ""}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("learning_sessions.views.LLMService")
    def test_send_message_to_completed_session_fails(self, mock_service_class):
        """Cannot send message to completed session."""
        self.session.status = Session.Status.COMPLETED
        self.session.save()

        url = reverse(
            "learning_sessions:session_messages",
            kwargs={"session_id": self.session.id},
        )
        data = {"content": "Hello"}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_messages_returns_session_messages(self):
        """Getting messages returns all session messages."""
        Message.objects.create(
            session=self.session,
            role=Message.Role.USER,
            content="Hello",
            sequence=1,
            is_active=True,
        )
        Message.objects.create(
            session=self.session,
            role=Message.Role.ASSISTANT,
            content="Hi there",
            sequence=2,
            is_active=True,
        )

        url = reverse(
            "learning_sessions:session_messages",
            kwargs={"session_id": self.session.id},
        )

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]["content"] == "Hello"
        assert response.data[1]["content"] == "Hi there"

    @patch("learning_sessions.views.LLMService")
    def test_send_message_handles_llm_error(self, mock_service_class):
        """LLM service error returns 503."""
        from llm.service import LLMServiceError

        mock_service = MagicMock()
        mock_service.process_message.side_effect = LLMServiceError("API Error")
        mock_service_class.return_value = mock_service

        url = reverse(
            "learning_sessions:session_messages",
            kwargs={"session_id": self.session.id},
        )
        data = {"content": "Hello"}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
