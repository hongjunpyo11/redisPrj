# chat/views.py
from django.shortcuts import render


def index(request):
    return render(request, "chat/index.html")


from django.shortcuts import render
from django.core.cache import cache


def room(request, room_name):
    cache_key = f"chat_{room_name}"
    messages = cache.get(cache_key, [])
    return render(request, "chat/room.html", {"room_name": room_name, "messages": messages})
