from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message


class HomeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.group_name = f"home_{self.scope['user'].id}"
        self.user_group_name = f"user_{self.scope['user'].id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add(
            self.user_group_name, self.channel_name
        )
        await self.channel_layer.group_add("presence", self.channel_name)

        await self.accept()
        await self.user_online()

        await self.channel_layer.group_send(
            "presence",
            {
                "type": "presence_update",
                "user_id": self.scope["user"].id,
                "is_online": True,
            },
        )

    async def disconnect(self, close_code):
        await self.user_offline()

        await self.channel_layer.group_send(
            "presence",
            {
                "type": "presence_update",
                "user_id": self.scope["user"].id,
                "is_online": False,
                "last_seen": timezone.localtime().strftime("%H:%M"),
            },
        )

        await self.channel_layer.group_discard(
            self.group_name, self.channel_name
        )
        await self.channel_layer.group_discard(
            self.user_group_name, self.channel_name
        )
        await self.channel_layer.group_discard(
            "presence", self.channel_name
        )

    async def home_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "home_update",
                    "conversation_id": event["conversation_id"],
                    "message_id": event["message_id"],
                    "sender": event["sender"],
                    "sender_id": event["sender_id"],
                    "message": event["message"],
                    "created_at": event["created_at"],
                    "unread": event["unread"],
                }
            )
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (TypeError, json.JSONDecodeError):
            return
        if data.get("type") != "delivered":
            return

        message_id = data.get("message_id")
        conversation_id = data.get("conversation_id")
        if not isinstance(message_id, int) or not isinstance(conversation_id, int):
            return

        result = await self.mark_delivered(message_id, conversation_id)
        if result is None:
            return

        sender_id, message_id = result
        await self.channel_layer.group_send(
            f"chat_{conversation_id}",
            {
                "type": "receipt_update",
                "message_ids": [message_id],
                "status": "delivered",
                "reader_id": self.scope["user"].id,
            },
        )
        await self.channel_layer.group_send(
            f"home_{sender_id}",
            {
                "type": "home_receipt_update",
                "conversation_id": conversation_id,
                "status": "delivered",
            },
        )

    @database_sync_to_async
    def mark_delivered(self, message_id, conversation_id):
        message = (
            Message.objects.filter(
                id=message_id,
                conversation_id=conversation_id,
                conversation__participants=self.scope["user"],
            )
            .exclude(sender=self.scope["user"])
            .first()
        )
        if message is None:
            return None
        if message.delivered_at is None:
            message.delivered_at = timezone.now()
            message.save(update_fields=["delivered_at"])
        return message.sender_id, message.id

    async def home_receipt_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "receipt_update",
                    "conversation_id": event["conversation_id"],
                    "status": event["status"],
                }
            )
        )

    async def user_notification(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "message_id": event["message_id"],
                    "conversation_id": event["conversation_id"],
                }
            )
        )

    @database_sync_to_async
    def user_online(self):
        profile = self.scope["user"].profile
        profile.active_connections += 1
        profile.is_online = True
        profile.save()

    @database_sync_to_async
    def user_offline(self):
        profile = self.scope["user"].profile
        profile.active_connections = max(0, profile.active_connections - 1)

        if profile.active_connections == 0:
            profile.is_online = False
            profile.last_seen = timezone.now()

        profile.save()

    async def presence_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence_update",
                    "user_id": event["user_id"],
                    "is_online": event["is_online"],
                    "last_seen": event.get("last_seen"),
                }
            )
        )

    async def home_typing(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "conversation_id": event["conversation_id"],
                    "sender": event["sender"],
                    "typing": event["typing"],
                }
            )
        )