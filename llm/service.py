import logging

from learning_sessions.models import Message
from learning_sessions.models import Session

from llm.client import AnthropicClient
from llm.client import BaseLLMClient
from llm.context_manager import ContextManager
from llm.parser import LLMResponseParser
from llm.parser import ParseError
from llm.prompt_builder import PromptBuilder
from llm.schemas import LLMResponse

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Raised when the LLM service encounters an error."""

    pass


class LLMService:
    """
    Orchestrates LLM interactions for a session.
    Handles message flow: save user message -> build context -> call LLM -> parse -> save response.
    """

    def __init__(
        self,
        client: BaseLLMClient | None = None,
        context_manager: ContextManager | None = None,
        parser: LLMResponseParser | None = None,
    ):
        """Initialize with optional custom components."""
        self.client = client or AnthropicClient()
        self.context_manager = context_manager or ContextManager()
        self.parser = parser or LLMResponseParser()

    def process_message(
        self,
        session: Session,
        user_content: str,
    ) -> tuple[Message, LLMResponse]:
        """
        Process a user message and generate assistant response.
        Returns the saved assistant message and parsed LLM response.
        """
        user_message = self.context_manager.add_message(
            session=session,
            role=Message.Role.USER,
            content=user_content,
        )
        logger.info(
            'Saved user message',
            extra={'session_id': str(session.id), 'sequence': user_message.sequence},
        )

        try:
            llm_response = self._generate_response(session)
        except Exception as e:
            logger.error(
                'Failed to generate LLM response',
                extra={'session_id': str(session.id), 'error': str(e)},
            )
            raise LLMServiceError(f'Failed to generate response: {e}') from e

        assistant_message = self.context_manager.add_message(
            session=session,
            role=Message.Role.ASSISTANT,
            content=llm_response.message,
            assessment_metadata=llm_response.assessment.model_dump(),
        )
        logger.info(
            'Saved assistant message',
            extra={
                'session_id': str(session.id),
                'sequence': assistant_message.sequence,
                'objectives_addressed': llm_response.assessment.objectives_addressed,
            },
        )

        self._update_session_state(session, llm_response)

        return assistant_message, llm_response

    def _generate_response(self, session: Session) -> LLMResponse:
        """Generate LLM response for the current session state."""
        prompt_builder = PromptBuilder(session.scenario)
        system_prompt = prompt_builder.build_system_prompt()

        messages = self.context_manager.get_context(session)

        client_response = self.client.complete(
            system_prompt=system_prompt,
            messages=messages,
        )

        try:
            return self.parser.parse(client_response.content)
        except ParseError:
            logger.warning(
                'Initial parse failed, attempting lenient parse',
                extra={'session_id': str(session.id)},
            )
            return self.parser.parse_lenient(client_response.content)

    def _update_session_state(
        self,
        session: Session,
        llm_response: LLMResponse,
    ) -> None:
        """Update session assessment state with latest response."""
        assessment = llm_response.assessment

        current_state = session.assessment_state or {}
        current_state['latest_score'] = assessment.overall_score
        current_state['scenario_state'] = assessment.scenario_state
        current_state['flags'] = assessment.flags

        objective_progress = current_state.get('objective_progress', {})
        for obj_id, progress in assessment.objective_progress.items():
            objective_progress[obj_id] = progress.model_dump()
        current_state['objective_progress'] = objective_progress

        session.assessment_state = current_state
        session.save(update_fields=['assessment_state', 'updated_date'])
