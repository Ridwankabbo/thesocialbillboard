from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError
from django.conf import settings

User = get_user_model()

from .utils import send_signup_otp_email


# ===== Signup =====
class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    user_type = serializers.ChoiceField(choices=User.USER_TYPE_CHOICES)

    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'confirm_password', 'user_type']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise ValidationError({"password": "Passwords do not match."})
        
        if len(data['password']) < 8:
            raise ValidationError({"password": "Password must be at least 8 characters long."})

        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=validated_data.get('user_type', ""),
            name=validated_data.get('name', "")
        )
        user.generate_otp()
        # send_mail(
        #     "Signup OTP",
        #     f"Your OTP is {user.otp}",
        #     "support@softvencefsd.xyz",
        #     [user.email],
        #     fail_silently=False,
        # )

        send_signup_otp_email(user)

        return user

# ===== OTP Verification with Role Selection =====
class SignupOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)


# ===== Login =====
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

# ===== Profile =====
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [ 'name', 'email', 'profile_pic', 'user_type', 'is_active', 'youtube_link', 'instagram_link', 'tiktok_link']

# ===== Role =====
class RoleSelectionSerializer(serializers.Serializer):
    user_type = serializers.ChoiceField(choices=User.USER_TYPE_CHOICES)

    def update(self, instance, validated_data):
        instance.user_type = validated_data['user_type']
        instance.save()
        return instance

# ===== Password Reset =====
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        user.generate_otp()
        # send_mail(
        #     "Password Reset OTP",
        #     f"Your OTP for password reset is {user.otp}",
        #     "support@softvencefsd.xyz",
        #     [user.email],
        #     fail_silently=False,
        # )

        send_signup_otp_email(user)

        return value

class PasswordResetChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if len(data['new_password']) < 8:
            raise serializers.ValidationError({
                "message":"Password must contain 8 charecters"
            })
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # if len(data['password']) < 8:
        #     raise ValidationError({"password": "Password must be at least 8 characters long."})

        return data




class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if len(data['new_password']) < 8:
            raise serializers.ValidationError({"message":"Password must contain 8 charecters"})
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        
        # if len(data['password']) < 8:
        #     raise ValidationError({"password": "Password must be at least 8 characters long."})

        return data
    




class TikTokCodeSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField(required=False, allow_blank=True)
    redirect_uri = serializers.URLField(required=False)






from rest_framework import serializers


class InstagramCodeSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField(required=False, allow_blank=True)









# serializers.py

from rest_framework import serializers

class YouTubeCodeSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField(required=False, allow_blank=True)


from apps.viral_builder.models import PlatformAccount


class PlatformAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAccount
        fields = ["id", "platform", "external_id", "display_name", "profile_url", "meta", "created_at"]







class PasswordResetResendOTPSerializer(serializers.Serializer):
    """
    Re-sends the password reset OTP if the user lost it.
    """
    email = serializers.EmailField()

    def validate(self, attrs):
        try:
            User.objects.get(email=attrs["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
        return attrs

    def save(self, **kwargs):
        user = User.objects.get(email=self.validated_data["email"])
        user.generate_otp()
        # send_mail(
        #     "Password Reset OTP (resend)",
        #     f"Your OTP for password reset is {user.otp}",
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[user.email],
        #     fail_silently=False,
        # )

        send_signup_otp_email(user)

        return user
