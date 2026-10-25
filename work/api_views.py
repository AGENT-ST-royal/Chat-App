
from asgiref.sync import async_to_sync
from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from channels.layers import get_channel_layer

from rest_framework import status
from rest_framework.authentication import (
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .api_serializers import (
    CurrentUserProfileSerializer,
    ConversationListSerializer,
    ConversationMessagePreviewSerializer,
    SendMessageSerializer,
)
from .models import Conversation, Message


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({
            "status": "ok",
            "service": "chat-backend",
            "api_version": "v1",
            "message": "The backend is ready to receive API requests.",
        })


class MobileLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        if not isinstance(username, str) or not isinstance(password, str):
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = username.strip()

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(
            request=request,
            username=username,
            password=password,
        )

        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "token_type": "Token",
            "user": {
                "id": user.id,
                "username": user.username,
            },
        })


class CurrentUserProfileView(APIView):
    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        profile = request.user.profile

        serializer = CurrentUserProfileSerializer(
            profile,
            context={"request": request},
        )

        return Response(serializer.data)


class MobileLogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        request.auth.delete()

        return Response(
            {"detail": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )


class ConversationListView(APIView):
    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        conversations = (
            Conversation.objects
            .filter(participants=request.user)
            .distinct()
            .prefetch_related(
                "participants__profile",
                "messages__sender",
            )
            .order_by("-updated_at", "-id")
        )

        serializer = ConversationListSerializer(
            conversations,
            many=True,
            context={"request": request},
        )

        return Response({
            "count": len(serializer.data),
            "results": serializer.data,
        })


class MessageHistoryPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class ConversationMessageHistoryView(APIView):
    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]
    permission_classes = [IsAuthenticated]
    pagination_class = MessageHistoryPagination

    def get(self, request, conversation_id, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation.objects.filter(
                participants=request.user,
            ).distinct(),
            pk=conversation_id,
        )

        messages = (
            conversation.messages
            .select_related("sender")
            .order_by("-created_at", "-id")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            messages,
            request,
            view=self,
        )

        serializer = ConversationMessagePreviewSerializer(
            page,
            many=True,
            context={"request": request},
        )

        return paginator.get_paginated_response(serializer.data)


class SendMessageView(APIView):
    authentication_classes = [
        TokenAuthentication,
        SessionAuthentication,
    ]
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id, *args, **kwargs):
        # Never trust a conversation ID without checking membership.
        conversation = get_object_or_404(
            Conversation.objects.filter(
                participants=request.user,
            ).distinct(),
            pk=conversation_id,
        )

        input_serializer = SendMessageSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        text = input_serializer.validated_data["text"]

        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=text,
            )

            # Conversation.updated_at uses auto_now=True.
            conversation.save(update_fields=["updated_at"])

        # Prepare the same event formats used by the existing consumers.
        created_at = timezone.localtime(
            message.created_at
        ).strftime("%H:%M")

        channel_layer = get_channel_layer()

        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.id}",
                {
                    "type": "chat_message",
                    "message_id": message.id,
                    "message": message.text,
                    "sender": request.user.username,
                    "sender_id": request.user.id,
                    "created_at": created_at,
                },
            )

            participant_ids = list(
                conversation.participants.values_list(
                    "id",
                    flat=True,
                )
            )

            for participant_id in participant_ids:
                async_to_sync(channel_layer.group_send)(
                    f"home_{participant_id}",
                    {
                        "type": "home_update",
                        "conversation_id": conversation.id,
                        "message_id": message.id,
                        "sender": request.user.username,
                        "sender_id": request.user.id,
                        "message": message.text,
                        "created_at": created_at,
                        "unread": participant_id != request.user.id,
                    },
                )

                if participant_id != request.user.id:
                    async_to_sync(channel_layer.group_send)(
                        f"user_{participant_id}",
                        {
                            "type": "user_notification",
                            "message_id": message.id,
                            "conversation_id": conversation.id,
                        },
                    )

        output_serializer = ConversationMessagePreviewSerializer(
            message,
            context={"request": request},
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )
