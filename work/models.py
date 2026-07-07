from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Conversation(models.Model):
    GROUP = "GROUP"
    PRIVATE = "PRIVATE"

    CHAT_TYPES = [
        (PRIVATE,"Private"),
        (GROUP,"Group")
    ]

    name = models.CharField(max_length= 100, blank=True)
    chat_type = models.CharField(
        max_length=10,
        choices=CHAT_TYPES,
        default=PRIVATE
    )

    participants = models.ManyToManyField(User)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def last_message(self):
        return self.messages.order_by("-created_at").first()
    def __str__(self):
        if self.chat_type == self.GROUP:
            return self.name
        return f"Conversation {self.id}"

class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete= models.CASCADE,
        related_name= "messages",
    )

    sender = models.ForeignKey(
        User,
        on_delete= models.CASCADE
    )

    text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add= True)

    edited = models.BooleanField(default=False)

    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.username}: {self.text[:30]}"
    
class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    avatar = models.ImageField(
        upload_to="avatars/",
    )
    bio = models.CharField(
        max_length=200,
        blank=True
    )

    is_online= models.BooleanField(default=False)

    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username
    
