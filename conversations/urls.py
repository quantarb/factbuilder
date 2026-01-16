from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('api/conversations/', views.get_conversations, name='get_conversations'),
    path('api/conversations/<int:conversation_id>/messages/', views.get_messages, name='get_messages'),
    path('api/send/', views.send_message, name='send_message'),
    path('api/taxonomy_graph/', views.taxonomy_graph_view, name='taxonomy_graph'),
]
