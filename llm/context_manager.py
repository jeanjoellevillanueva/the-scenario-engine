from abc import ABC
from abc import abstractmethod

from learning_sessions.models import Message
from learning_sessions.models import Session


class BaseContextStrategy(ABC):
    """
    Abstract base class for context management strategies.
    """

    @abstractmethod
    def get_messages(self, session: Session) -> list[dict]:
        """
        Return messages to include in the API call.
        """
        raise NotImplementedError


class FullHistoryStrategy(BaseContextStrategy):
    """
    Include all messages in the context.
    """

    def get_messages(self, session: Session) -> list[dict]:
        """
        Return all messages for the session.
        """
        messages = (
            session.messages
            .filter(is_active=True)
            .order_by('sequence')
            .values('role', 'content')
        )
        return [{'role': m['role'], 'content': m['content']} for m in messages]


class SlidingWindowStrategy(BaseContextStrategy):
    """
    Include only the last N messages.
    """

    def __init__(self, window_size: int = 20):
        """
        Initialize with window size.
        """
        self.window_size = window_size

    def get_messages(self, session: Session) -> list[dict]:
        """
        Return the last N messages for the session.
        """
        messages = (
            session.messages
            .filter(is_active=True)
            .order_by('-sequence')[:self.window_size]
        )
        ordered = sorted(messages, key=lambda m: m.sequence)
        return [{'role': m.role, 'content': m.content} for m in ordered]


class ContextManager:
    """
    Manages conversation context for LLM calls.
    Delegates to a configurable strategy.
    """

    def __init__(
        self,
        strategy: BaseContextStrategy | None = None,
        max_messages: int | None = None,
    ):
        """
        Initialize with a strategy.
        """
        if strategy is not None:
            self.strategy = strategy
        elif max_messages is not None:
            self.strategy = SlidingWindowStrategy(window_size=max_messages)
        else:
            self.strategy = FullHistoryStrategy()

    def get_context(self, session: Session) -> list[dict]:
        """
        Get conversation context for the session.
        """
        return self.strategy.get_messages(session)

    def add_message(
        self,
        session: Session,
        role: str,
        content: str,
        assessment_metadata: dict | None = None,
    ) -> Message:
        """
        Add a new message to the session.
        """
        last_message = (
            session.messages
            .filter(is_active=True)
            .order_by('-sequence')
            .first()
        )
        next_sequence = (last_message.sequence + 1) if last_message else 1

        return Message.objects.create(
            session=session,
            role=role,
            content=content,
            sequence=next_sequence,
            assessment_metadata=assessment_metadata or {},
            is_active=True,
        )
