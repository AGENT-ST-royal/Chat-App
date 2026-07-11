from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from django.utils import timezone

class HomeConsumer(AsyncWebsocketConsumer):
    async def connect(self):

        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.group_name = f"home_{self.scope['user'].id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.channel_layer.group_add(
            "presence",
            self.channel_name
        )

        await self.accept()

        await self.user_online()

        await self.channel_layer.group_send(
            "presence",
            {
                "type": "presence_update",
                "user_id": self.scope["user"].id,
                "is_online": True,
            }
        )

    async def disconnect(self, close_code):
        await self.user_offline()

        await self.channel_layer.group_send(
            "presence",
            {
                "type": "presence_update",
                "user_id": self.scope["user"].id,
                "is_online": False,
                "last_seen": timezone.localtime().strftime("%#I:%M %p"),
            }
        )

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        await self.channel_layer.group_discard(
            "presence",
            self.channel_name
        )

    async def home_update(self, event):
        await self.send(text_data=json.dumps({
            "conversation_id": event["conversation_id"],
            "sender": event["sender"],
            "message": event["message"],
            "created_at": event["created_at"],
        }))


    @database_sync_to_async
    def user_online(self):
        profile = self.scope["user"].profile
        profile.is_online = True
        profile.last_seen = timezone.now()
        profile.save()

    @database_sync_to_async
    def user_offline(self):
        profile = self.scope["user"].profile
        profile.is_online = False
        profile.last_seen = timezone.now()
        profile.save()
    
    async def presence_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "presence_update",
            "user_id": event["user_id"],
            "is_online": event["is_online"],
            "last_seen": event.get("last_seen"),
        }))