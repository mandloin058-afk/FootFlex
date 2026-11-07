from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Log in with e-mail (case-insensitive) or username (so `createsuperuser` accounts also work)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if not username or not password:
            return None
        user = User.objects.filter(email__iexact=username).first() or User.objects.filter(username__iexact=username).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
