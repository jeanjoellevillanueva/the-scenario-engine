from django.contrib.auth.password_validation import validate_password

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import User


class RegisterView(APIView):
    """
    Register a new user and issue JWT access/refresh.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Create the user and return a JWT pair.
        """
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'detail': 'Email and password are required.'},
                status=HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'detail': 'Email is already registered.'},
                status=HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(password)
        except Exception as exc:
            return Response(
                {'detail': str(exc)},
                status=HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            email=email,
            password=password,
            is_active=True,
            is_email_verified=False,
        )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=HTTP_201_CREATED,
        )
