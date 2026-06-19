from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        from core.models import UserProfile
        UserProfile.objects.get_or_create(user=user)
        return user

    def is_open_for_signup(self, request, sociallogin):
        return True
