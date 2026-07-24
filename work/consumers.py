from django.utils import timezone
from channels.db import database_sync_to_async
from .models import Conversation, Message
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print("Connected")

    @database_sync_to_async
    def get_conversation(self, conversation_id):
        return Conversation.objects.get(id=conversation_id)
    
    
    @database_sync_to_async
    def save_message(self,conversation, sender, text):
        return Message.objects.create(
            conversation = conversation,
            sender=sender,
            text=text,
            is_read =False
        )
    
    @database_sync_to_async
    def get_receiver(self, conversation, sender):
        return conversation.participants.exclude(id=sender.id).first()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    

    async def receive(self, text_data):
        data = json.loads(text_data)

        message_type = data.get("type")

        # Get the conversation first
        conversation = await self.get_conversation(self.conversation_id)

        # Handle typing events
        if message_type == "typing":

            receiver = await self.get_receiver(
                conversation,
                self.scope["user"]
            )

            # Send to the open chat
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_status",
                    "sender": self.scope["user"].username,
                    "typing": data["typing"],
                }
            )

            # Send to the receiver's home page
            await self.channel_layer.group_send(
                f"home_{receiver.id}",
                {
                    "type": "home_typing",
                    "conversation_id": conversation.id,
                    "sender": self.scope["user"].username,
                    "typing": data["typing"],
                }
            )

            return

        # Normal message handling
        text = data["message"]

        message = await self.save_message(
            conversation,
            self.scope["user"],
            text
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message":event["message"],
            "sender": event["sender"],
            "created_at": event["created_at"]
        }))

    async def typing_status(self, event):

        await self.send(text_data=json.dumps({
            "type":"typing",
            "sender":event["sender"],
            "typing":event["typing"],
        }))