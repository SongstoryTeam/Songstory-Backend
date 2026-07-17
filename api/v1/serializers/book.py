from rest_framework import serializers

from core.models import Book


class BookCreateSerializer(serializers.ModelSerializer):
    """
    title/description are not real Book fields (they live on BookTranslation),
    but the client still submits them as plain fields. We keep them declared
    here for input validation and strip them out before Book.objects.create()/
    update() — the view is responsible for writing them to BookTranslation.
    """

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Book
        fields = (
            "title",
            "description",
            "year",
            "cover_url",
            "isbn",
        )

    def validate_year(self, value: int) -> int:
        if value < 0 or value > 2100:
            raise serializers.ValidationError("Invalid year.")
        return value

    def create(self, validated_data: dict) -> Book:
        validated_data.pop("title", None)
        validated_data.pop("description", None)
        return Book.objects.create(**validated_data)

    def update(self, instance: Book, validated_data: dict) -> Book:
        validated_data.pop("title", None)
        validated_data.pop("description", None)
        return super().update(instance, validated_data)
