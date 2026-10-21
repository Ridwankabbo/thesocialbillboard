from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    If the incoming social login's email already exists in our DB,
    attach the social account to that existing user so Google login can proceed.
    """
    def pre_social_login(self, request, sociallogin):
        # If sociallogin already linked to a user, nothing to do
        if sociallogin.is_existing:
            return

        # Try to get email from social account extra_data (provider dependent)
        email = None
        if sociallogin.account and sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get("email")

        # Fallback to sociallogin.user.email (sometimes populated)
        if not email:
            email = getattr(sociallogin.user, "email", None)

        # If no email, we can't check — let normal flow continue
        if not email:
            return

        # If a user with this email already exists, connect this social login to them
        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        if existing_user and getattr(existing_user, "pk", None) != getattr(getattr(sociallogin, "user", None), "pk", None):
            sociallogin.connect(request, existing_user)
