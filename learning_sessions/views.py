import logging

from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from learning_sessions.models import Session
from learning_sessions.serializers import MessageResponseSerializer
from learning_sessions.serializers import MessageSerializer
from learning_sessions.serializers import SendMessageSerializer
from learning_sessions.serializers import SessionCreateSerializer
from learning_sessions.serializers import SessionSerializer

from llm.service import LLMService
from llm.service import LLMServiceError

logger = logging.getLogger(__name__)


class SessionListCreateView(APIView):
    """API view for listing and creating sessions."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all sessions for the current user."""
        sessions = Session.objects.filter(
            learner=request.user,
            is_active=True,
        ).select_related('scenario')
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new session."""
        serializer = SessionCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        session = serializer.save()

        response_serializer = SessionSerializer(session)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    """API view for retrieving a single session."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        """Get session details with all messages."""
        session = get_object_or_404(
            Session.objects.select_related('scenario').prefetch_related(
                'messages',
                'scenario__learning_objectives',
            ),
            id=session_id,
            learner=request.user,
            is_active=True,
        )
        serializer = SessionSerializer(session)
        return Response(serializer.data)


class SessionMessageView(APIView):
    """API view for sending messages to a session."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        """Send a message and get LLM response."""
        session = get_object_or_404(
            Session.objects.select_related('scenario').prefetch_related(
                'scenario__learning_objectives',
            ),
            id=session_id,
            learner=request.user,
            is_active=True,
        )

        if session.status == Session.Status.COMPLETED:
            return Response(
                {'error': 'Session is already completed'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_content = serializer.validated_data['content']

        try:
            llm_service = LLMService()
            assistant_message, llm_response = llm_service.process_message(
                session=session,
                user_content=user_content,
            )
        except LLMServiceError as e:
            logger.error(
                'LLM service error',
                extra={'session_id': str(session_id), 'error': str(e)},
            )
            return Response(
                {'error': 'Failed to generate response. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_data = {
            'message': MessageSerializer(assistant_message).data,
            'assessment': llm_response.assessment.model_dump(),
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    def get(self, request, session_id):
        """Get all messages for a session."""
        session = get_object_or_404(
            Session,
            id=session_id,
            learner=request.user,
            is_active=True,
        )
        messages = session.messages.filter(is_active=True).order_by('sequence')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
