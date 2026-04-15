import secrets
import urllib.parse

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse

import requests
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from oauth.utils import get_tokens_for_google_payload
from oauth.utils import issue_tokens_for_google_payload
from oauth.utils import verify_google_id_token


class GoogleSignInView(APIView):
    """
    Exchange a Google ID token for JWT access/refresh.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Verify token and return JWT pair.
        """
        token = request.data.get('id_token')
        if not token:
            return Response(
                {'detail': 'Missing id_token.'},
                status=HTTP_400_BAD_REQUEST,
            )

        payload, error_msg = verify_google_id_token(token)
        if error_msg:
            return Response(
                {'detail': error_msg},
                status=HTTP_400_BAD_REQUEST,
            )

        return issue_tokens_for_google_payload(payload)


class GoogleLoginView(APIView):
    """
    Redirect the user to Google's OAuth consent screen.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Redirect to Google authorization endpoint.
        """
        callback_url = settings.GOOGLE_OAUTH_REDIRECT_URI
        state = secrets.token_urlsafe(32)
        request.session['google_oauth_state'] = state

        params = {
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'redirect_uri': callback_url,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'include_granted_scopes': 'true',
            'prompt': 'consent',
            'state': state,
        }
        url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(
            params
        )
        return HttpResponseRedirect(url)


class GoogleCallbackView(APIView):
    """
    OAuth callback that exchanges code for tokens and redirects with JWTs.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Handle Google redirect, exchange code, store tokens in session, redirect.
        """
        state = request.query_params.get('state')
        code = request.query_params.get('code')
        stored_state = request.session.get('google_oauth_state')
        login_url = reverse('login')

        if not state or not code:
            request.session['auth_error'] = 'Missing code or state.'
            return HttpResponseRedirect(login_url)

        if not stored_state or stored_state != state:
            request.session['auth_error'] = 'Invalid state.'
            return HttpResponseRedirect(login_url)

        callback_url = settings.GOOGLE_OAUTH_REDIRECT_URI
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': callback_url,
            },
            timeout=10,
        )
        if token_response.status_code != 200:
            request.session['auth_error'] = 'Failed to exchange code.'
            return HttpResponseRedirect(login_url)

        token_payload = token_response.json()
        google_id_token = token_payload.get('id_token')
        if not google_id_token:
            request.session['auth_error'] = 'Missing id_token from Google.'
            return HttpResponseRedirect(login_url)

        payload, error_msg = verify_google_id_token(google_id_token)
        if error_msg:
            request.session['auth_error'] = error_msg
            return HttpResponseRedirect(login_url)

        tokens, error_msg = get_tokens_for_google_payload(payload)
        if error_msg:
            request.session['auth_error'] = error_msg
            return HttpResponseRedirect(login_url)

        request.session['jwt_tokens'] = tokens
        return HttpResponseRedirect(reverse('auth_complete'))
