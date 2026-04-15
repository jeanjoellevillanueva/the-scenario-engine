from django.urls import reverse_lazy
from django.views.generic import TemplateView


class LoginPageView(TemplateView):
    """
    Render the login page.
    """

    template_name = 'frontend/login.html'

    def get_context_data(self, **kwargs):
        """
        Provide template context for the login page.
        """
        context = super().get_context_data(**kwargs)
        context['dashboard_url'] = reverse_lazy('dashboard')
        context['google_login_url'] = reverse_lazy('oauth:google_login')
        context['register_url'] = reverse_lazy('register')
        context['token_url'] = reverse_lazy('token_obtain_pair')
        context['auth_error'] = self.request.session.pop('auth_error', None)
        return context


class RegisterPageView(TemplateView):
    """
    Render the registration page.
    """

    template_name = 'frontend/register.html'

    def get_context_data(self, **kwargs):
        """
        Provide template context for the registration page.
        """
        context = super().get_context_data(**kwargs)
        context['dashboard_url'] = reverse_lazy('dashboard')
        context['login_url'] = reverse_lazy('login')
        context['register_api_url'] = reverse_lazy('register_api')
        return context


class AuthCompleteView(TemplateView):
    """
    Complete OAuth flow by storing tokens in localStorage.
    """

    template_name = 'frontend/auth_complete.html'

    def get_context_data(self, **kwargs):
        """
        Provide JWT tokens from session to template.
        """
        context = super().get_context_data(**kwargs)
        tokens = self.request.session.pop('jwt_tokens', None)
        context['access_token'] = tokens.get('access', '') if tokens else ''
        context['refresh_token'] = tokens.get('refresh', '') if tokens else ''
        context['dashboard_url'] = reverse_lazy('dashboard')
        context['login_url'] = reverse_lazy('login')
        return context


class DashboardPageView(TemplateView):
    """
    Render the dashboard placeholder page.
    """

    template_name = 'frontend/dashboard.html'

    def get_context_data(self, **kwargs):
        """
        Provide template context for the dashboard page.
        """
        context = super().get_context_data(**kwargs)
        context['login_url'] = reverse_lazy('login')
        return context

