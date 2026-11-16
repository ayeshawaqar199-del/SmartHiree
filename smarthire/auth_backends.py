from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Allow the same password form to accept a username or unique email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email") or kwargs.get("username")
        if identifier and "@" in identifier:
            User = get_user_model()
            matches = User.objects.filter(email__iexact=identifier.strip())
            if matches.count() != 1:
                return None
            identifier = matches.first().get_username()
        return super().authenticate(request, username=identifier, password=password, **kwargs)
