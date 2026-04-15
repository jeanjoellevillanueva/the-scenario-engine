from unittest.mock import patch

from django.test import TestCase

from core.models import User
from oauth.utils import issue_tokens_for_google_payload
from oauth.utils import verify_google_id_token


class VerifyGoogleIdTokenTests(TestCase):
    """
    Unit tests for Google ID token verification helper.
    """

    @patch('oauth.utils.google_id_token.verify_oauth2_token')
    def test_returns_payload_when_verification_succeeds(self, verify_oauth2_token):
        """
        Return payload and no error response.
        """
        expected_payload = {
            'email': 'user@example.com',
            'family_name': 'Doe',
            'given_name': 'Jane',
        }
        verify_oauth2_token.return_value = expected_payload

        payload, error_response = verify_google_id_token('token')

        self.assertEqual(payload, expected_payload)
        self.assertIsNone(error_response)

    @patch('oauth.utils.google_id_token.verify_oauth2_token')
    def test_returns_error_message_when_verification_fails(self, verify_oauth2_token):
        """
        Return an error message and no payload.
        """
        verify_oauth2_token.side_effect = Exception('bad token')

        payload, error_msg = verify_google_id_token('token')

        self.assertIsNone(payload)
        self.assertEqual(error_msg, 'Invalid Google token.')


class IssueTokensForGooglePayloadTests(TestCase):
    """
    Unit tests for issuing JWT tokens from Google payload.
    """

    def test_returns_400_when_email_missing(self):
        """
        Reject payload without email.
        """
        response = issue_tokens_for_google_payload({'given_name': 'Jane'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {'detail': 'Google token missing email.'})

    @patch('oauth.utils.RefreshToken.for_user')
    def test_creates_user_and_returns_tokens(self, for_user):
        """
        Create user and return access/refresh tokens.
        """
        refresh = type(
            'Refresh',
            (),
            {
                'access_token': 'access-token',
                '__str__': lambda self: 'refresh-token',
            },
        )()
        for_user.return_value = refresh

        payload = {
            'email': 'user@example.com',
            'family_name': 'Doe',
            'given_name': 'Jane',
        }
        response = issue_tokens_for_google_payload(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'access': 'access-token', 'refresh': 'refresh-token'})
        self.assertTrue(User.objects.filter(email='user@example.com').exists())

    @patch('oauth.utils.RefreshToken.for_user')
    def test_updates_existing_user_fields_when_empty(self, for_user):
        """
        Update names and email verification for existing user when needed.
        """
        refresh = type(
            'Refresh',
            (),
            {
                'access_token': 'access-token',
                '__str__': lambda self: 'refresh-token',
            },
        )()
        for_user.return_value = refresh

        user = User.objects.create(
            email='user@example.com',
            first_name='',
            is_email_verified=False,
            last_name='',
        )
        self.assertFalse(user.is_email_verified)

        payload = {
            'email': 'user@example.com',
            'family_name': 'Doe',
            'given_name': 'Jane',
        }
        response = issue_tokens_for_google_payload(payload)

        user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.first_name, 'Jane')
        self.assertEqual(user.last_name, 'Doe')
        self.assertTrue(user.is_email_verified)
