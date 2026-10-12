import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"

        if not user.is_authenticated or not await self.is_participant(user.id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        self.user_group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

        # Opening the conversation delivers its history and counts as reading it.
        receipt = await self.mark_conversation_read(user.id)
        if receipt["message_ids"]:
            await self.send_receipt_update(receipt)
            for sender_id in receipt["sender_ids"]:
                await self.channel_layer.group_send(
                    f"home_{sender_id}",
                    {
                        "type": "home_receipt_update",
                        "conversation_id": int(self.conversation_id),
                        "status": "read",
                    },
                )

    @database_sync_to_async
    def is_participant(self, user_id):
        return Conversation.objects.filter(
            id=self.conversation_id, participants__id=user_id
        ).exists()

    @database_sync_to_async
    def conversation_participant_ids(self):
        return list(
            Conversation.objects.filter(id=self.conversation_id)
            .values_list("participants__id", flat=True)
        )

    @database_sync_to_async
    def mark_conversation_read(self, reader_id):
        now = timezone.now()
        messages = Message.objects.filter(
            conversation_id=self.conversation_id,
        ).exclude(sender_id=reader_id).filter(is_read=False)
        rows = list(messages.values_list("id", "sender_id"))
        messages.update(is_read=True, delivered_at=now, read_at=now)
        return {
            "message_ids": [row[0] for row in rows],
            "sender_ids": list({row[1] for row in rows}),
            "status": "read",
            "reader_id": reader_id,
        }

    @database_sync_to_async
    def mark_message_delivered(self, message_id, recipient_id, conversation_id):
        message = Message.objects.filter(
            id=message_id,
            conversation_id=conversation_id,
            conversation__participants__id=recipient_id,
        ).exclude(sender_id=recipient_id).first()
        if not message:
            return None
        if message.delivered_at is None:
            message.delivered_at = timezone.now()
            message.save(update_fields=["delivered_at"])
        return message.sender_id

    @database_sync_to_async
    def mark_message_read(self, message_id, reader_id, conversation_id):
        message = Message.objects.filter(
            id=message_id,
            conversation_id=conversation_id,
            conversation__participants__id=reader_id,
        ).exclude(sender_id=reader_id).first()
        if not message:
            return None
        now = timezone.now()
        fields = []
        if message.delivered_at is None:
            message.delivered_at = now
            fields.append("delivered_at")
        if not message.is_read:
            message.is_read = True
            message.read_at = now
            fields.extend(["is_read", "read_at"])
        if fields:
            message.save(update_fields=fields)
        return message.sender_id

    @database_sync_to_async
    def save_message(self, sender, text):
        return Message.objects.create(
            conversation_id=self.conversation_id,
            sender=sender,
            text=text,
        )

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name
            )

    async def receive(self, text_data):
        if not self.scope["user"].is_authenticated:
            await self.close(code=4403)
            return
        try:
            data = json.loads(text_data)
        except (TypeError, json.JSONDecodeError):
            return

        message_type = data.get("type")
        user = self.scope["user"]

        if message_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_status",
                    "sender": user.username,
                    "typing": bool(data.get("typing")),
                },
            )
            for participant_id in await self.conversation_participant_ids():
                if participant_id != user.id:
                    await self.channel_layer.group_send(
                        f"home_{participant_id}",
                        {
                            "type": "home_typing",
                            "conversation_id": int(self.conversation_id),
                            "sender": user.username,
                            "typing": bool(data.get("typing")),
                        },
                    )
            return

        if message_type in {"delivered", "read"}:
            message_id = data.get("message_id")
            conversation_id = data.get(
                "conversation_id", int(self.conversation_id)
            )
            if not isinstance(message_id, int):
                return
            if not isinstance(conversation_id, int):
                return

            if message_type == "read":
                sender_id = await self.mark_message_read(
                    message_id, user.id, conversation_id
                )
                status = "read"
            else:
                sender_id = await self.mark_message_delivered(
                    message_id, user.id, conversation_id
                )
                status = "delivered"

            if sender_id is not None:
                await self.channel_layer.group_send(
                    f"chat_{conversation_id}",
                    {
                        "type": "receipt_update",
                        "message_ids": [message_id],
                        "status": status,
                        "reader_id": user.id,
                    },
                )
                await self.channel_layer.group_send(
                    f"home_{sender_id}",
                    {
                        "type": "home_receipt_update",
                        "conversation_id": conversation_id,
                        "status": status,
                    },
                )
            return

        text = data.get("message", "").strip()
        if not text:
            return
        message = await self.save_message(user, text)
        created_at = timezone.localtime(message.created_at).strftime("%H:%M")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message_id": message.id,
                "message": message.text,
                "sender": user.username,
                "sender_id": user.id,
                "created_at": created_at,
            },
        )

        participant_ids = await self.conversation_participant_ids()
        for participant_id in participant_ids:
            await self.channel_layer.group_send(
                f"home_{participant_id}",
                {
                    "type": "home_update",
                    "conversation_id": int(self.conversation_id),
                    "message_id": message.id,
                    "sender": user.username,
                    "sender_id": user.id,
                    "message": message.text,
                    "created_at": created_at,
                    "unread": participant_id != user.id,
                },
            )
            if participant_id != user.id:
                await self.channel_layer.group_send(
                    f"user_{participant_id}",
                    {
                        "type": "user_notification",
                        "message_id": message.id,
                        "conversation_id": int(self.conversation_id),
                    },
                )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message_id": event["message_id"],
                    "message": event["message"],
                    "sender": event["sender"],
                    "sender_id": event["sender_id"],
                    "created_at": event["created_at"],
                }
            )
        )

    async def receipt_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "receipt",
                    "message_ids": event["message_ids"],
                    "status": event["status"],
                    "reader_id": event["reader_id"],
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

    async def send_receipt_update(self, receipt):
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "receipt_update", **receipt},
        )

    async def typing_status(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "sender": event["sender"],
                    "typing": event["typing"],
                }
            )
        )