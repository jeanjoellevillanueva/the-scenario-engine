from unittest.mock import Mock
from unittest.mock import patch

from django.test import override_settings

from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.test import APITestCase


class GoogleSignInViewTests(APITestCase):
    """
    Unit tests for Google sign-in endpoint.
    """

    def test_missing_id_token_returns_400(self):
        """
        Reject requests without id_token.
        """
        response = self.client.post('/api/oauth/google/', data={}, format='json')

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Missing id_token.'})

    @patch('oauth.views.issue_tokens_for_google_payload')
    @patch('oauth.views.verify_google_id_token')
    def test_valid_token_returns_tokens(self, verify_google_id_token, issue_tokens_for_google_payload):
        """
        Return token pair when verification succeeds.
        """
        verify_google_id_token.return_value = (
            {'email': 'user@example.com'},
            None,
        )
        issue_tokens_for_google_payload.return_value = Response(
            {'access': 'a', 'refresh': 'r'},
            status=HTTP_200_OK,
        )

        response = self.client.post(
            '/api/oauth/google/',
            data={'id_token': 'token'},
            format='json',
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data, {'access': 'a', 'refresh': 'r'})

    @patch('oauth.views.verify_google_id_token')
    def test_invalid_token_returns_400(self, verify_google_id_token):
        """
        Surface invalid token response from verifier.
        """
        verify_google_id_token.return_value = (None, 'Invalid Google token.')

        response = self.client.post(
            '/api/oauth/google/',
            data={'id_token': 'token'},
            format='json',
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Invalid Google token.'})


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
)
class GoogleCallbackViewTests(APITestCase):
    """
    Unit tests for Google OAuth callback endpoint.
    """

    def test_missing_code_or_state_redirects_with_error(self):
        """
        Redirect to login with error when code/state missing.
        """
        response = self.client.get('/api/oauth/google/callback/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.assertEqual(self.client.session.get('auth_error'), 'Missing code or state.')

    def test_invalid_state_redirects_with_error(self):
        """
        Redirect to login with error when state mismatched.
        """
        session = self.client.session
        session['google_oauth_state'] = 'stored'
        session.save()

        response = self.client.get('/api/oauth/google/callback/?state=wrong&code=abc')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.assertEqual(self.client.session.get('auth_error'), 'Invalid state.')

    @patch('oauth.views.requests.post')
    def test_failed_code_exchange_redirects_with_error(self, requests_post):
        """
        Redirect to login with error when Google code exchange fails.
        """
        session = self.client.session
        session['google_oauth_state'] = 'stored'
        session.save()

        requests_post.return_value = Mock(status_code=400, json=lambda: {})

        response = self.client.get('/api/oauth/google/callback/?state=stored&code=abc')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.assertEqual(self.client.session.get('auth_error'), 'Failed to exchange code.')

    @patch('oauth.views.requests.post')
    def test_missing_id_token_in_exchange_response_redirects_with_error(self, requests_post):
        """
        Redirect to login with error when Google response has no id_token.
        """
        session = self.client.session
        session['google_oauth_state'] = 'stored'
        session.save()

        requests_post.return_value = Mock(status_code=200, json=lambda: {'access_token': 'x'})

        response = self.client.get('/api/oauth/google/callback/?state=stored&code=abc')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.assertEqual(
            self.client.session.get('auth_error'),
            'Missing id_token from Google.',
        )

    @patch('oauth.views.get_tokens_for_google_payload')
    @patch('oauth.views.verify_google_id_token')
    @patch('oauth.views.requests.post')
    def test_successful_callback_redirects_with_tokens(
        self,
        requests_post,
        verify_google_id_token,
        get_tokens_for_google_payload,
    ):
        """
        Store tokens in session and redirect to auth complete.
        """
        session = self.client.session
        session['google_oauth_state'] = 'stored'
        session.save()

        requests_post.return_value = Mock(
            status_code=200,
            json=lambda: {'id_token': 'google-id-token'},
        )
        verify_google_id_token.return_value = ({'email': 'user@example.com'}, None)
        get_tokens_for_google_payload.return_value = ({'access': 'a', 'refresh': 'r'}, None)

        response = self.client.get('/api/oauth/google/callback/?state=stored&code=abc')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/auth-complete/')
        self.assertEqual(
            self.client.session.get('jwt_tokens'),
            {'access': 'a', 'refresh': 'r'},
        )
