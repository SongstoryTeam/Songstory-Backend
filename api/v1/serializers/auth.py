from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class UserMeSerializer(serializers.ModelSerializer):
    is_verified_author = serializers.BooleanField(
        source="profile.is_verified_author", read_only=True, default=False
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_verified_author"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name"]

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
