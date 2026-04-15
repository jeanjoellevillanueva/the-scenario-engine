from django.urls import path

from learning_sessions.views import SessionDetailView
from learning_sessions.views import SessionListCreateView
from learning_sessions.views import SessionMessageView

app_name = 'learning_sessions'

urlpatterns = [
    path(
        '',
        SessionListCreateView.as_view(),
        name='session_list_create',
    ),
    path(
        '<uuid:session_id>/',
        SessionDetailView.as_view(),
        name='session_detail',
    ),
    path(
        '<uuid:session_id>/messages/',
        SessionMessageView.as_view(),
        name='session_messages',
    ),
]
