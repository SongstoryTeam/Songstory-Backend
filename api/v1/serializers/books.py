from rest_framework import serializers

from core.models import Book, Chapter, MusicRecommendation, Playlist


class BookListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    genre = serializers.SerializerMethodField()
    coverUrl = serializers.SerializerMethodField()
    chaptersCount = serializers.SerializerMethodField()
    averageRating = serializers.FloatField(source="average_rating", read_only=True)
    ratingsCount = serializers.SerializerMethodField()
    viewsCount = serializers.IntegerField(source="views_count", read_only=True)

    class Meta:
        model = Book
        fields = [
            "id", "slug", "title", "author", "genre", "year",
            "coverUrl", "viewsCount", "averageRating", "ratingsCount",
            "chaptersCount",
        ]

    def get_title(self, obj: Book) -> str:
        return obj.get_title(self._lang())

    def get_author(self, obj: Book) -> str:
        return obj.get_author_name(self._lang())

    def get_genre(self, obj: Book) -> str | None:
        return obj.get_genre_name(self._lang()) or None

    def get_coverUrl(self, obj: Book) -> str | None:
        request = self.context.get("request")
        cover = obj.get_cover()
        if cover and request:
            return request.build_absolute_uri(cover)
        return cover

    def get_chaptersCount(self, obj: Book) -> int:
        return obj.chapters.filter(is_approved=True).count()

    def get_ratingsCount(self, obj: Book) -> int:
        return obj.ratings.count()

    def _lang(self) -> str:
        request = self.context.get("request")
        return getattr(request, "LANGUAGE_CODE", "uk") if request else "uk"


class ChapterSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    moodTags = serializers.SerializerMethodField()
    isApproved = serializers.BooleanField(source="is_approved", read_only=True)
    musicCount = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ["id", "number", "title", "description", "moodTags", "isApproved", "musicCount"]

    def get_title(self, obj: Chapter) -> str:
        return obj.get_title(self._lang())

    def get_description(self, obj: Chapter) -> str:
        return obj.get_description(self._lang())

    def get_moodTags(self, obj: Chapter) -> str:
        return obj.get_mood_tags(self._lang())

    def get_musicCount(self, obj: Chapter) -> int:
        return obj.music_recommendations.count()

    def _lang(self) -> str:
        request = self.context.get("request")
        return getattr(request, "LANGUAGE_CODE", "uk") if request else "uk"


class MusicRecommendationSerializer(serializers.ModelSerializer):
    trackTitle = serializers.CharField(source="track_title")
    linkType = serializers.CharField(source="link_type")
    linkUrl = serializers.URLField(source="link_url")
    embedCode = serializers.CharField(source="embed_code", allow_blank=True, required=False)
    likesCount = serializers.IntegerField(source="likes_count", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = MusicRecommendation
        fields = [
            "id", "trackTitle", "artist", "linkType", "linkUrl", "embedCode",
            "comment", "mood", "likesCount", "createdAt", "user",
        ]

    def get_user(self, obj: MusicRecommendation) -> dict:
        return {"id": obj.user_id, "username": obj.user.username}


class PlaylistSerializer(serializers.ModelSerializer):
    externalLink = serializers.URLField(source="external_link", allow_blank=True, required=False)
    likesCount = serializers.IntegerField(source="likes_count", read_only=True)
    isPublic = serializers.BooleanField(source="is_public")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    creator = serializers.SerializerMethodField()
    book = serializers.SerializerMethodField()
    tracks = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = [
            "id", "slug", "title", "description", "mood", "externalLink",
            "likesCount", "isPublic", "createdAt", "creator", "book", "tracks",
        ]

    def get_creator(self, obj: Playlist) -> dict:
        return {"id": obj.creator_id, "username": obj.creator.username}

    def get_book(self, obj: Playlist) -> dict:
        return {"id": obj.book_id, "slug": obj.book.slug, "title": obj.book.get_title()}

    def get_tracks(self, obj: Playlist) -> list:
        return [
            {
                "id": t.id,
                "trackTitle": t.track_title,
                "artist": t.artist,
                "linkUrl": t.link_url,
                "order": t.order,
            }
            for t in obj.tracks.all()
        ]
