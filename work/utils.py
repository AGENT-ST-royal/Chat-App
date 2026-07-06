from .models import Conversation
from django.contrib.auth.models import User

def get_or_create_conversation(user1, user2):
    conversation = Conversation.objects.filter(
        participants= user1
    ).filter(
        participants=user2
    ).first()

    if conversation is None:
        conversation = Conversation.objects.create()
        conversation.participants.add(user1, user2)
    
    return conversation