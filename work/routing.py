from django.urls import path,re_path
from .consumers import ChatConsumer
from .home_consumer import HomeConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/chat/(?P<conversation_id>\d+)/$",
        ChatConsumer.as_asgi()
    ),
    path("ws/home/", HomeConsumer.as_asgi()),
]