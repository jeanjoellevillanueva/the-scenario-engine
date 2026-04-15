from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from scenarios.models import LearningObjective
from scenarios.models import Scenario

User = get_user_model()


class TestScenarioAPI(APITestCase):
    """Tests for the scenario API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_list_scenarios_returns_active_only(self):
        """Listing scenarios returns only active scenarios."""
        active = Scenario.objects.create(
            name="Active Scenario",
            persona="Persona",
            setting="Setting",
            context="Context",
            is_active=True,
        )
        inactive = Scenario.objects.create(
            name="Inactive Scenario",
            persona="Persona",
            setting="Setting",
            context="Context",
            is_active=False,
        )
        url = reverse("scenarios:scenario_list")

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        names = [s["name"] for s in response.data]
        assert "Active Scenario" in names
        assert "Inactive Scenario" not in names

    def test_list_scenarios_includes_objectives(self):
        """Scenario list includes learning objectives."""
        scenario = Scenario.objects.create(
            name="Test Scenario",
            persona="Persona",
            setting="Setting",
            context="Context",
            is_active=True,
        )
        LearningObjective.objects.create(
            scenario=scenario,
            objective_id="LO1",
            description="First objective",
            is_active=True,
        )
        url = reverse("scenarios:scenario_list")

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert len(response.data[0]["learning_objectives"]) == 1
        assert response.data[0]["learning_objectives"][0]["objective_id"] == "LO1"

    def test_list_scenarios_requires_auth(self):
        """Listing scenarios requires authentication."""
        self.client.force_authenticate(user=None)
        url = reverse("scenarios:scenario_list")

        response = self.client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
