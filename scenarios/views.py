from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scenarios.models import Scenario
from scenarios.serializers import ScenarioListSerializer


class ScenarioListView(APIView):
    """API view for listing available scenarios."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all active scenarios."""
        scenarios = Scenario.objects.filter(is_active=True).prefetch_related(
            'learning_objectives',
        )
        serializer = ScenarioListSerializer(scenarios, many=True)
        return Response(serializer.data)
