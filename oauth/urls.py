from django.urls import path

from oauth.views import GoogleCallbackView
from oauth.views import GoogleLoginView
from oauth.views import GoogleSignInView


app_name = 'oauth'


urlpatterns = [
    path(
        'google/login/',
        GoogleLoginView.as_view(),
        name='google_login',
    ),
    path(
        'google/callback/',
        GoogleCallbackView.as_view(),
        name='google_callback',
    ),
    path(
        'google/',
        GoogleSignInView.as_view(),
        name='google_sign_in',
    ),
]
