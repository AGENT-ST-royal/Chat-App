from urllib import request

from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import Message, Conversation
from django.contrib.auth.decorators import login_required 
from .utils import get_or_create_conversation
from .forms import ProfileForm


# Create your views here.
def index(request):
    return render(request, "index.html")

@login_required
def home(request):
    conversations = Conversation.objects.filter(
        participants=request.user
    )

    search = request.GET.get("search", "")

    users = User.objects.exclude(id=request.user.id)

    if search:
        users = users.filter(username__icontains=search)

    chat_list = []

    for conversation in conversations:
        other_user =conversation.participants.exclude(
            id= request.user.id
        ).first()

        last_message = conversation.last_message()

        unread_count = Message.objects.filter(
            conversation = conversation,
            is_read =False
        ).exclude(
            sender = request.user
        ).count()

        chat_list.append({
            "conversation": conversation,
            "user": other_user,
            "last_message": last_message,
            "unread_count": unread_count,
        })

    chat_list.sort(
        key=lambda x: x["last_message"].created_at if x["last_message"] else x["conversation"].created_at, reverse=True
    )

    print("SEARCH =", search)
    print("FOUND USERS =", list(users.values_list("username", flat=True)))
    print("CURRENT USER =", request.user.username)

    return render(request, "pages/home.html",{
        "chat_list": chat_list,
        "users": users,
        "search": search            
    })
    
@login_required
def start_chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    conversation = get_or_create_conversation(
        request.user,
        other_user
    )

    return redirect(
        "chat_room",
        conversation_id = conversation.id
    )

@login_required
def chat_room(request, conversation_id):
    
    conversation = get_object_or_404(
        Conversation,
        id= conversation_id,
        participants = request.user
    )

    other_user = conversation.participants.exclude(
        id= request.user.id
    ).first()

    Message.objects.filter(
        conversation = conversation,
        is_read =False
    ).exclude(
        sender = request.user
    ).update(
        is_read=True
    )
  
    messages =Message.objects.filter(
        conversation=conversation
    ).order_by("created_at")

    context = {
        "conversation": conversation,
        "other_user": other_user,
        "messages": messages,
    }

    return render(request, "pages/chat_room.html", context)


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username= username,
            password= password
        )

        if user is not None:
            login(request, user)
            user.profile.is_online = True
            user.profile.save()
            return redirect("home")
        messages.error(request, "Invalid username or password.")
    return render(request, "auth/login.html")

def register(request):
    if request.method == 'POST':
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        comfirm = request.POST.get("comfirm_password")

        if password != comfirm:
            messages.error(request, "Passwords do not match")
            return redirect("register")
        
        if User.objects.filter(username = username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")
        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully")
        return redirect("login")
    return render(request, "auth/register.html")

@login_required
def profile(request):
    profile = request.user.profile

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile 
        )

        if form.is_valid():
            profile = form.save()

            print("Avatar:", profile.avatar)
            print("URL:", profile.avatar.url)

            return redirect("profile")
        else:
            print(form.errors)
    else:
        form = ProfileForm(instance=profile)

    return render(request, "pages/profile.html",{
        "form":form
    })