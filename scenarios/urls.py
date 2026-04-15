from django.urls import path

from scenarios.views import ScenarioListView

app_name = 'scenarios'

urlpatterns = [
    path(
        '',
        ScenarioListView.as_view(),
        name='scenario_list',
    ),
]
