from django.conf import settings
from django.db import models

from core.models import BaseModel


class Session(BaseModel):
    """
    One learner's run through a scenario.
    """

    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    scenario = models.ForeignKey(
        'scenarios.Scenario',
        on_delete=models.CASCADE,
        related_name='sessions',
    )
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_sessions',
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    assessment_state = models.JSONField(
        default=dict,
        blank=True,
        help_text='JSON snapshot of current progress',
    )

    class Meta:
        ordering = ['-created_date']

    def __str__(self):
        return f'{self.learner} - {self.scenario.name}'


class Message(BaseModel):
    """
    A single message in a session conversation.
    """

    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
    )
    content = models.TextField(
        help_text='The raw message text',
    )
    assessment_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Structured JSON returned by LLM alongside message',
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
    )
    sequence = models.PositiveIntegerField(
        help_text='Ordering within session',
    )

    class Meta:
        ordering = ['session', 'sequence']
        unique_together = [['session', 'sequence']]

    def __str__(self):
        return f'{self.session} - {self.role} #{self.sequence}'
