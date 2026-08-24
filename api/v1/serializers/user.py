from django.contrib.auth.models import User
from rest_framework import serializers

from core.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("bio", "avatar", "is_verified_author")
        read_only_fields = ("is_verified_author",)


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "profile",
            "followers_count",
            "date_joined",
        )

    def get_followers_count(self, obj: User) -> int:
        return obj.followers.count()


class UserUpdateSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(
        source="profile.bio", required=False, allow_blank=True
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "bio")

    def update(self, instance: User, validated_data: dict) -> User:
        profile_data = validated_data.pop("profile", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password_confirm")

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )