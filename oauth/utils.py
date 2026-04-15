from django.conf import settings
from django.utils import timezone

from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import User


def verify_google_id_token(token):
    """
    Verify a Google ID token and return its payload or error message.
    """
    try:
        payload = google_id_token.verify_oauth2_token(
            token,
            Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except Exception:
        return None, 'Invalid Google token.'

    return payload, None


def get_or_create_user_from_google_payload(payload):
    """
    Create or update a user from a Google payload.
    """
    email = payload.get('email')
    if not email:
        return None, 'Google token missing email.'

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'first_name': payload.get('given_name', ''),
            'is_active': True,
            'is_email_verified': True,
            'last_name': payload.get('family_name', ''),
        },
    )
    if not created:
        changed_fields = []
        if not user.is_email_verified:
            user.is_email_verified = True
            changed_fields.append('is_email_verified')

        if payload.get('given_name') and not user.first_name:
            user.first_name = payload.get('given_name', '')
            changed_fields.append('first_name')

        if payload.get('family_name') and not user.last_name:
            user.last_name = payload.get('family_name', '')
            changed_fields.append('last_name')

        if not user.last_login:
            user.last_login = timezone.now()
            changed_fields.append('last_login')

        if changed_fields:
            user.save(update_fields=changed_fields)

    return user, None


def get_tokens_for_google_payload(payload):
    """
    Create or update a user from a Google payload and return JWT tokens as dict.
    """
    user, error = get_or_create_user_from_google_payload(payload)
    if error:
        return None, error

    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }, None


def issue_tokens_for_google_payload(payload):
    """
    Create or update a user from a Google payload and issue JWT tokens as Response.
    """
    tokens, error = get_tokens_for_google_payload(payload)
    if error:
        return Response(
            {'detail': error},
            status=HTTP_400_BAD_REQUEST,
        )

    return Response(tokens, status=HTTP_200_OK)
