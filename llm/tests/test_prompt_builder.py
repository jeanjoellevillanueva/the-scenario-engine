import pytest

from django.test import TestCase

from llm.prompt_builder import PromptBuilder

from scenarios.models import LearningObjective
from scenarios.models import Scenario


class TestPromptBuilder(TestCase):
    """Tests for the prompt builder."""

    def setUp(self):
        """Set up test fixtures."""
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            persona="You are Dave, a friendly farmer.",
            setting="A rural farm in Australia.",
            context="A cow named Duchess is unwell.",
            is_active=True,
        )
        self.objective1 = LearningObjective.objects.create(
            scenario=self.scenario,
            objective_id="LO1",
            description="Gather patient history",
            detection_hints="Ask about symptoms, timeline",
            is_active=True,
        )
        self.objective2 = LearningObjective.objects.create(
            scenario=self.scenario,
            objective_id="LO2",
            description="Perform assessment",
            detection_hints="Check vital signs",
            is_active=True,
        )
        self.builder = PromptBuilder(self.scenario)

    def test_build_system_prompt_includes_persona(self):
        """System prompt includes persona section."""
        prompt = self.builder.build_system_prompt()

        assert "## YOUR CHARACTER" in prompt
        assert "You are Dave, a friendly farmer." in prompt
        assert "Stay in character" in prompt

    def test_build_system_prompt_includes_setting(self):
        """System prompt includes setting section."""
        prompt = self.builder.build_system_prompt()

        assert "## SETTING" in prompt
        assert "A rural farm in Australia." in prompt

    def test_build_system_prompt_includes_context(self):
        """System prompt includes context/situation section."""
        prompt = self.builder.build_system_prompt()

        assert "## SITUATION" in prompt
        assert "A cow named Duchess is unwell." in prompt

    def test_build_system_prompt_includes_objectives(self):
        """System prompt includes learning objectives."""
        prompt = self.builder.build_system_prompt()

        assert "## LEARNING OBJECTIVES TO ASSESS" in prompt
        assert "LO1" in prompt
        assert "Gather patient history" in prompt
        assert "LO2" in prompt
        assert "Perform assessment" in prompt

    def test_build_system_prompt_includes_detection_hints(self):
        """System prompt includes detection hints for objectives."""
        prompt = self.builder.build_system_prompt()

        assert "Ask about symptoms, timeline" in prompt
        assert "Check vital signs" in prompt

    def test_build_system_prompt_includes_output_contract(self):
        """System prompt includes structured output contract."""
        prompt = self.builder.build_system_prompt()

        assert "## RESPONSE FORMAT" in prompt
        assert '"message"' in prompt
        assert '"assessment"' in prompt
        assert '"objectives_addressed"' in prompt
        assert "ONLY output valid JSON" in prompt

    def test_build_system_prompt_excludes_inactive_objectives(self):
        """System prompt excludes inactive objectives."""
        self.objective1.is_active = False
        self.objective1.save()

        prompt = self.builder.build_system_prompt()

        assert "LO1" not in prompt
        assert "LO2" in prompt

    def test_get_objective_ids_returns_active_only(self):
        """get_objective_ids returns only active objective IDs."""
        self.objective2.is_active = False
        self.objective2.save()

        ids = self.builder.get_objective_ids()

        assert ids == ["LO1"]

    def test_build_system_prompt_handles_empty_objectives(self):
        """System prompt handles scenario with no objectives."""
        self.objective1.delete()
        self.objective2.delete()

        prompt = self.builder.build_system_prompt()

        assert "## YOUR CHARACTER" in prompt
        assert "LEARNING OBJECTIVES" not in prompt

    def test_build_system_prompt_sections_are_separated(self):
        """System prompt sections are properly separated."""
        prompt = self.builder.build_system_prompt()

        sections = prompt.split("\n\n")
        assert len(sections) >= 4
