from core.models import BaseModel

from django.db import models


class Scenario(BaseModel):
    """
    Reusable template that configures a simulation.
    One scenario record can power many sessions.
    """

    name = models.CharField(max_length=255)
    persona = models.TextField(
        help_text='Who the LLM plays (e.g., Dave the farmer)',
    )
    setting = models.TextField(
        help_text='Physical context description',
    )
    context = models.TextField(
        help_text='Full situation brief used in the system prompt',
    )
    evaluation_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text='Scoring rubric for the learner',
    )

    class Meta:
        ordering = ['-created_date']

    def __str__(self):
        return self.name


class LearningObjective(BaseModel):
    """
    A single learning objective tied to a scenario.
    """

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='learning_objectives',
    )
    objective_id = models.CharField(
        max_length=32,
        help_text='Short identifier (e.g., LO1, LO2)',
    )
    description = models.TextField(
        help_text='What the learner should demonstrate',
    )
    detection_hints = models.TextField(
        blank=True,
        default='',
        help_text='Hints for the LLM to detect if objective is met',
    )

    class Meta:
        ordering = ['objective_id']
        unique_together = [['scenario', 'objective_id']]

    def __str__(self):
        return f'{self.scenario.name} - {self.objective_id}'
