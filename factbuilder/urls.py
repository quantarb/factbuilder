"""
factbuilder URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from conversations import views as chat_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', chat_views.chat_view, name='chat'),
    path('chat/api/conversations/', chat_views.get_conversations, name='get_conversations'),
    path('chat/api/conversations/<int:conversation_id>/messages/', chat_views.get_messages, name='get_messages'),
    path('chat/api/send/', chat_views.send_message, name='send_message'),
    path('chat/api/approve_proposal/', chat_views.approve_proposal, name='approve_proposal'),
    path('chat/api/taxonomy_graph/', chat_views.taxonomy_graph_view, name='taxonomy_graph'),
]
