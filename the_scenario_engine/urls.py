from django.contrib import admin
from django.urls import include
from django.urls import path

from core.views import RegisterView

from frontend.views import AuthCompleteView
from frontend.views import ChatPageView
from frontend.views import DashboardPageView
from frontend.views import LoginPageView
from frontend.views import RegisterPageView
from frontend.views import ScenarioSelectPageView

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path(
        '',
        LoginPageView.as_view(),
        name='login',
    ),
    path(
        'register/',
        RegisterPageView.as_view(),
        name='register',
    ),
    path(
        'auth-complete/',
        AuthCompleteView.as_view(),
        name='auth_complete',
    ),
    path(
        'dashboard/',
        DashboardPageView.as_view(),
        name='dashboard',
    ),
    path(
        'scenarios/',
        ScenarioSelectPageView.as_view(),
        name='scenario_select',
    ),
    path(
        'chat/<uuid:session_id>/',
        ChatPageView.as_view(),
        name='chat',
    ),
    path(
        'admin/',
        admin.site.urls,
    ),
    path(
        'api/token/',
        TokenObtainPairView.as_view(),
        name='token_obtain_pair',
    ),
    path(
        'api/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh',
    ),
    path(
        'api/oauth/',
        include('oauth.urls'),
    ),
    path(
        'api/register/',
        RegisterView.as_view(),
        name='register_api',
    ),
    path(
        'api/scenarios/',
        include('scenarios.urls'),
    ),
    path(
        'api/sessions/',
        include('learning_sessions.urls'),
    ),
]
