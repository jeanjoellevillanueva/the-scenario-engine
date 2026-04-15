from textwrap import dedent

from scenarios.models import Scenario


class PromptBuilder:
    """
    Builds system prompts from Scenario models.
    """

    STRUCTURED_OUTPUT_CONTRACT = dedent('''
        You must ALWAYS respond with valid JSON in this exact format:
        {
          "message": "<your in-character response to the learner>",
          "assessment": {
            "objectives_addressed": ["<list of objective IDs addressed in this turn>"],
            "objective_progress": {
              "<objective_id>": {
                "status": "<not_yet|partial|met>",
                "evidence": "<brief evidence or null>"
              }
            },
            "overall_score": <0-5>,
            "scenario_state": "<current phase: e.g., greeting, history_gathering, assessment, diagnosis, treatment_planning>",
            "flags": ["<any behavioral flags: e.g., student_seems_uncertain, rushed_response>"]
          }
        }

        CRITICAL RULES:
        1. ONLY output valid JSON - no markdown, no explanation outside the JSON
        2. The "message" field contains your in-character dialogue
        3. Update objective_progress for ALL objectives, not just those addressed this turn
        4. Be honest in assessment - only mark "met" when truly demonstrated
    ''').strip()

    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    def build_system_prompt(self) -> str:
        """
        Build the complete system prompt from the scenario.
        """
        sections = [
            self._build_persona_section(),
            self._build_setting_section(),
            self._build_context_section(),
            self._build_objectives_section(),
            self._build_output_contract_section(),
        ]
        return '\n\n'.join(filter(None, sections))

    def _build_persona_section(self) -> str:
        """
        Build the persona instructions section.
        """
        return dedent(f'''
            ## YOUR CHARACTER
            {self.scenario.persona}

            Stay in character at all times. Respond naturally as this character would.
        ''').strip()

    def _build_setting_section(self) -> str:
        """
        Build the setting description section.
        """
        return dedent(f'''
            ## SETTING
            {self.scenario.setting}
        ''').strip()

    def _build_context_section(self) -> str:
        """
        Build the situation context section.
        """
        return dedent(f'''
            ## SITUATION
            {self.scenario.context}
        ''').strip()

    def _build_objectives_section(self) -> str:
        """
        Build the learning objectives section.
        """
        objectives = self.scenario.learning_objectives.filter(is_active=True)
        if not objectives.exists():
            return ''

        lines = [
            '## LEARNING OBJECTIVES TO ASSESS',
            'Track the learner\'s progress against these objectives:',
            '',
        ]

        for obj in objectives:
            lines.append(f'- **{obj.objective_id}**: {obj.description}')
            if obj.detection_hints:
                lines.append(f'  Detection hints: {obj.detection_hints}')

        return '\n'.join(lines)

    def _build_output_contract_section(self) -> str:
        """
        Build the structured output contract section.
        """
        return dedent(f'''
            ## RESPONSE FORMAT
            {self.STRUCTURED_OUTPUT_CONTRACT}
        ''').strip()

    def get_objective_ids(self) -> list[str]:
        """
        Get list of active objective IDs for this scenario.
        """
        return list(
            self.scenario.learning_objectives
            .filter(is_active=True)
            .values_list('objective_id', flat=True)
        )
