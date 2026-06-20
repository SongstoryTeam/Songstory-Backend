from rest_framework import serializers

from core.models import Comment


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "text", "user", "createdAt", "replies"]

    def get_user(self, obj: Comment) -> dict:
        return {"id": obj.user_id, "username": obj.user.username}

    def get_replies(self, obj: Comment) -> list:
        return CommentSerializer(obj.replies.all(), many=True, context=self.context).data
