from django.urls import path

from frontend.views import AuthCompleteView
from frontend.views import DashboardPageView
from frontend.views import LoginPageView


app_name = 'frontend'


urlpatterns = [
    path(
        '',
        LoginPageView.as_view(),
        name='login',
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
]
