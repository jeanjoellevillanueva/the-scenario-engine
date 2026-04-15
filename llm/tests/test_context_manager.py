from django.contrib.auth import get_user_model
from django.test import TestCase

from learning_sessions.models import Message
from learning_sessions.models import Session

from llm.context_manager import ContextManager
from llm.context_manager import FullHistoryStrategy
from llm.context_manager import SlidingWindowStrategy

from scenarios.models import Scenario

User = get_user_model()


class TestContextManager(TestCase):
    """Tests for the context manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            persona="Test persona",
            setting="Test setting",
            context="Test context",
            is_active=True,
        )
        self.session = Session.objects.create(
            scenario=self.scenario,
            learner=self.user,
            is_active=True,
        )

    def _create_message(self, role, content, sequence):
        """Helper to create a message."""
        return Message.objects.create(
            session=self.session,
            role=role,
            content=content,
            sequence=sequence,
            is_active=True,
        )

    def test_full_history_returns_all_messages(self):
        """Full history strategy returns all messages."""
        self._create_message("user", "Hello", 1)
        self._create_message("assistant", "Hi there", 2)
        self._create_message("user", "How are you?", 3)

        manager = ContextManager(strategy=FullHistoryStrategy())
        messages = manager.get_context(self.session)

        assert len(messages) == 3
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": "Hi there"}
        assert messages[2] == {"role": "user", "content": "How are you?"}

    def test_sliding_window_returns_last_n_messages(self):
        """Sliding window strategy returns only last N messages."""
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            self._create_message(role, f"Message {i}", i + 1)

        manager = ContextManager(strategy=SlidingWindowStrategy(window_size=4))
        messages = manager.get_context(self.session)

        assert len(messages) == 4
        assert messages[0]["content"] == "Message 6"
        assert messages[3]["content"] == "Message 9"

    def test_sliding_window_preserves_order(self):
        """Sliding window returns messages in correct order."""
        self._create_message("user", "First", 1)
        self._create_message("assistant", "Second", 2)
        self._create_message("user", "Third", 3)

        manager = ContextManager(strategy=SlidingWindowStrategy(window_size=2))
        messages = manager.get_context(self.session)

        assert messages[0]["content"] == "Second"
        assert messages[1]["content"] == "Third"

    def test_add_message_creates_message(self):
        """add_message creates a new message record."""
        manager = ContextManager()
        message = manager.add_message(
            session=self.session,
            role="user",
            content="Test message",
        )

        assert message.session == self.session
        assert message.role == "user"
        assert message.content == "Test message"
        assert message.sequence == 1

    def test_add_message_increments_sequence(self):
        """add_message correctly increments sequence number."""
        manager = ContextManager()
        msg1 = manager.add_message(self.session, "user", "First")
        msg2 = manager.add_message(self.session, "assistant", "Second")
        msg3 = manager.add_message(self.session, "user", "Third")

        assert msg1.sequence == 1
        assert msg2.sequence == 2
        assert msg3.sequence == 3

    def test_add_message_stores_assessment_metadata(self):
        """add_message stores assessment metadata."""
        manager = ContextManager()
        metadata = {"objectives_addressed": ["LO1"], "overall_score": 2}
        message = manager.add_message(
            session=self.session,
            role="assistant",
            content="Response",
            assessment_metadata=metadata,
        )

        assert message.assessment_metadata == metadata

    def test_context_excludes_inactive_messages(self):
        """Context excludes soft-deleted messages."""
        self._create_message("user", "Active", 1)
        inactive = self._create_message("assistant", "Inactive", 2)
        inactive.is_active = False
        inactive.save()
        self._create_message("user", "Also active", 3)

        manager = ContextManager()
        messages = manager.get_context(self.session)

        assert len(messages) == 2
        assert all(m["content"] != "Inactive" for m in messages)

    def test_default_strategy_is_full_history(self):
        """Default strategy is full history."""
        manager = ContextManager()

        assert isinstance(manager.strategy, FullHistoryStrategy)

    def test_max_messages_param_creates_sliding_window(self):
        """max_messages parameter creates sliding window strategy."""
        manager = ContextManager(max_messages=5)

        assert isinstance(manager.strategy, SlidingWindowStrategy)
        assert manager.strategy.window_size == 5
