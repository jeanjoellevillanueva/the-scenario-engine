from rest_framework import serializers

from learning_sessions.models import Message
from learning_sessions.models import Session

from scenarios.models import LearningObjective
from scenarios.models import Scenario


class LearningObjectiveSerializer(serializers.ModelSerializer):
    """Serializer for LearningObjective model."""

    class Meta:
        model = LearningObjective
        fields = ['objective_id', 'description', 'detection_hints']


class ScenarioSerializer(serializers.ModelSerializer):
    """Serializer for Scenario model."""

    learning_objectives = LearningObjectiveSerializer(many=True, read_only=True)

    class Meta:
        model = Scenario
        fields = ['id', 'name', 'persona', 'setting', 'context', 'learning_objectives']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""

    class Meta:
        model = Message
        fields = [
            'id',
            'role',
            'content',
            'assessment_metadata',
            'timestamp',
            'sequence',
        ]
        read_only_fields = ['id', 'timestamp', 'sequence', 'assessment_metadata']


class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model."""

    scenario_detail = ScenarioSerializer(source='scenario', read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Session
        fields = [
            'id',
            'scenario',
            'scenario_detail',
            'learner',
            'status',
            'assessment_state',
            'messages',
            'created_date',
            'updated_date',
        ]
        read_only_fields = [
            'id',
            'learner',
            'status',
            'assessment_state',
            'messages',
            'created_date',
            'updated_date',
        ]


class SessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Session."""

    class Meta:
        model = Session
        fields = ['scenario']

    def create(self, validated_data):
        """Create a new session for the current user."""
        validated_data['learner'] = self.context['request'].user
        validated_data['is_active'] = True
        return super().create(validated_data)


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a message to a session."""

    content = serializers.CharField(
        min_length=1,
        max_length=10000,
        help_text='The message content from the learner',
    )


class MessageResponseSerializer(serializers.Serializer):
    """Serializer for the response after sending a message."""

    message = MessageSerializer()
    assessment = serializers.DictField()
