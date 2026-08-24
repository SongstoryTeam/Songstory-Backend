from rest_framework import serializers

from core.models import MusicRecommendation, Playlist, PlaylistTrack


class MusicRecommendationSerializer(serializers.ModelSerializer):
    is_liked = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = MusicRecommendation
        fields = (
            "id",
            "track_title",
            "artist",
            "link_type",
            "link_url",
            "embed_code",
            "comment",
            "mood",
            "likes_count",
            "created_at",
            "username",
            "is_liked",
        )
        read_only_fields = ("likes_count", "created_at", "username", "is_liked")

    def get_is_liked(self, obj: MusicRecommendation) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()


class PlaylistTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaylistTrack
        fields = ("id", "track_title", "artist", "link_url", "embed_code", "order")


class PlaylistSerializer(serializers.ModelSerializer):
    tracks = PlaylistTrackSerializer(many=True, read_only=True)
    creator_username = serializers.CharField(source="creator.username", read_only=True)

    class Meta:
        model = Playlist
        fields = (
            "slug",
            "title",
            "description",
            "mood",
            "external_link",
            "is_public",
            "likes_count",
            "created_at",
            "creator_username",
            "tracks",
        )
        read_only_fields = ("slug", "likes_count", "created_at", "creator_username")