from django.contrib import admin

from scenarios.models import LearningObjective
from scenarios.models import Scenario


class LearningObjectiveInline(admin.TabularInline):
    """Inline admin for learning objectives within a scenario."""

    model = LearningObjective
    extra = 1
    fields = ['objective_id', 'description', 'detection_hints', 'is_active']


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    """Admin configuration for Scenario model."""

    list_display = ['name', 'is_active', 'created_date']
    list_filter = ['is_active']
    search_fields = ['name', 'persona', 'setting']
    inlines = [LearningObjectiveInline]


@admin.register(LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    """Admin configuration for LearningObjective model."""

    list_display = ['objective_id', 'scenario', 'is_active']
    list_filter = ['scenario', 'is_active']
    search_fields = ['objective_id', 'description']
