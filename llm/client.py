import logging
import time
from abc import ABC
from abc import abstractmethod

from anthropic import Anthropic
from anthropic import APIError
from anthropic import APITimeoutError
from anthropic import RateLimitError

from django.conf import settings

from llm.schemas import LLMClientResponse


logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.
    """

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> LLMClientResponse:
        raise NotImplementedError


class AnthropicClient(BaseLLMClient):
    """
    Anthropic Claude client.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        retry_delays: list[int] | None = None,
    ):
        """
        Initialize the Anthropic client.
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.max_tokens = max_tokens or settings.ANTHROPIC_MAX_TOKENS
        self.timeout = timeout or settings.ANTHROPIC_TIMEOUT
        self.max_retries = max_retries or settings.ANTHROPIC_MAX_RETRIES
        self.retry_delays = retry_delays or self._parse_retry_delays()
        self._client: Anthropic | None = None

    def _parse_retry_delays(self) -> list[int]:
        """Parse retry delays from settings."""
        delays_str = settings.ANTHROPIC_RETRY_DELAYS
        return [int(d.strip()) for d in delays_str.split(',')]

    @property
    def client(self) -> Anthropic:
        """
        Lazy initialization of the Anthropic client.
        """
        if self._client is None:
            self._client = Anthropic(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> LLMClientResponse:
        """
        Send a completion request with retry logic.
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                return self._make_request(system_prompt, messages)
            except RateLimitError as e:
                last_error = e
                self._log_rate_limit_details(e)
                self._handle_retry(attempt, 'Rate limit exceeded', e)
            except APITimeoutError as e:
                last_error = e
                self._handle_retry(attempt, 'Request timeout', e)
            except APIError as e:
                if e.status_code and e.status_code >= 500:
                    last_error = e
                    self._handle_retry(attempt, f'Server error {e.status_code}', e)
                else:
                    logger.error(
                        f'API error: {e.message}',
                        extra={
                            'status_code': e.status_code,
                            'body': str(e.body) if hasattr(e, 'body') else None,
                        },
                    )
                    raise

        logger.error(
            'All retries exhausted',
            extra={'attempts': self.max_retries, 'last_error': str(last_error)},
        )
        raise last_error

    def _log_rate_limit_details(self, error: RateLimitError) -> None:
        """Log detailed rate limit information."""
        details = {
            'error_message': str(error.message) if hasattr(error, 'message') else str(error),
            'status_code': error.status_code if hasattr(error, 'status_code') else None,
        }

        if hasattr(error, 'response') and error.response:
            headers = error.response.headers
            details['retry_after'] = headers.get('retry-after')
            details['rate_limit_requests'] = headers.get('x-ratelimit-limit-requests')
            details['rate_limit_tokens'] = headers.get('x-ratelimit-limit-tokens')
            details['remaining_requests'] = headers.get('x-ratelimit-remaining-requests')
            details['remaining_tokens'] = headers.get('x-ratelimit-remaining-tokens')
            details['reset_requests'] = headers.get('x-ratelimit-reset-requests')
            details['reset_tokens'] = headers.get('x-ratelimit-reset-tokens')

        if hasattr(error, 'body') and error.body:
            details['error_body'] = error.body

        logger.warning(
            'Rate limit details',
            extra=details,
        )
        print(f"\n{'='*50}")
        print("RATE LIMIT DETAILS:")
        for key, value in details.items():
            if value:
                print(f"  {key}: {value}")
        print(f"{'='*50}\n")

    def _make_request(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> LLMClientResponse:
        """
        Make a single API request.
        """
        start_time = time.time()

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=messages,
        )

        latency_ms = (time.time() - start_time) * 1000

        content = ''
        if response.content and len(response.content) > 0:
            content = response.content[0].text

        result = LLMClientResponse(
            content=content,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            latency_ms=latency_ms,
        )

        logger.info(
            'LLM request completed',
            extra={
                'model': result.model,
                'input_tokens': result.input_tokens,
                'output_tokens': result.output_tokens,
                'latency_ms': round(result.latency_ms, 2),
            },
        )

        return result

    def _handle_retry(
        self,
        attempt: int,
        reason: str,
        error: Exception,
    ) -> None:
        """
        Handle retry with delay and logging.
        """
        if attempt < self.max_retries - 1:
            delay = self.retry_delays[attempt]
            logger.warning(
                f'{reason}, retrying in {delay}s',
                extra={'attempt': attempt + 1, 'error': str(error)},
            )
            time.sleep(delay)
