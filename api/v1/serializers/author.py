from rest_framework import serializers

from core.models import Author
from .mixins import LangMixin


class AuthorSerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    books_count = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ("slug", "name", "photo_url", "bio", "birth_year", "books_count")

    def get_name(self, obj: Author) -> str:
        return obj.get_name(self._lang())

    def get_bio(self, obj: Author) -> str:
        return obj.get_bio(self._lang())

    def get_books_count(self, obj: Author) -> int:
        return obj.books.filter(is_approved=True).count()