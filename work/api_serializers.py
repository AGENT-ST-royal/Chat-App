
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Conversation, Message, Profile


class CurrentUserProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "user_id",
            "username",
            "first_name",
            "last_name",
            "bio",
            "avatar_url",
            "is_online",
            "last_seen",
        ]
        read_only_fields = fields

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None

        request = self.context.get("request")
        avatar_url = obj.avatar.url

        if request is not None:
            return request.build_absolute_uri(avatar_url)

        return avatar_url


class ConversationParticipantSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "avatar_url",
            "is_online",
        ]

    def get_avatar_url(self, obj):
        profile = getattr(obj, "profile", None)

        if profile is None or not profile.avatar:
            return None

        request = self.context.get("request")
        avatar_url = profile.avatar.url

        if request is not None:
            return request.build_absolute_uri(avatar_url)

        return avatar_url

    def get_is_online(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.is_online if profile is not None else False


class ConversationMessagePreviewSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)
    sender_username = serializers.CharField(
        source="sender.username",
        read_only=True,
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "sender_id",
            "sender_username",
            "text",
            "created_at",
            "edited",
            "is_read",
        ]


class ConversationListSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(
        many=True,
        read_only=True,
    )
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "name",
            "chat_type",
            "created_at",
            "updated_at",
            "participants",
            "latest_message",
        ]

    def get_latest_message(self, obj):
        message = obj.messages.order_by("-created_at", "-id").first()

        if message is None:
            return None

        return ConversationMessagePreviewSerializer(
            message,
            context=self.context,
        ).data


class SendMessageSerializer(serializers.Serializer):
    text = serializers.CharField(
        max_length=5000,
        allow_blank=False,
        trim_whitespace=True,
    )
