from django.urls import path
from .views import *

urlpatterns = [
    path("index/", index, name="index"),
    path("", login_view, name="login"),
    path("register/", register, name="register"),
    path("home/", home, name="home"),
    path("<int:conversation_id>/", chat_room, name="chat_room"),
    path("start/<int:user_id>/", start_chat, name="start_chat"),
    path("profile", profile, name="profile"),
]