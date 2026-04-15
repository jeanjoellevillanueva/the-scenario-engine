from rest_framework import serializers

from scenarios.models import LearningObjective
from scenarios.models import Scenario


class LearningObjectiveListSerializer(serializers.ModelSerializer):
    """Serializer for listing learning objectives."""

    class Meta:
        model = LearningObjective
        fields = ['objective_id', 'description']


class ScenarioListSerializer(serializers.ModelSerializer):
    """Serializer for listing scenarios."""

    learning_objectives = LearningObjectiveListSerializer(many=True, read_only=True)

    class Meta:
        model = Scenario
        fields = ['id', 'name', 'setting', 'learning_objectives']
