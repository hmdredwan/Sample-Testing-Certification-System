from django.urls import path
from . import views

urlpatterns = [
    path('', views.UserMessagesView.as_view(), name='user-messages'),
    path('sent/', views.UserSentMessagesView.as_view(), name='user-sent-messages'),
    path('conversation/<uuid:test_request_id>/', views.ConversationView.as_view(), name='conversation'),
    path('send/', views.SendMessageView.as_view(), name='send-message'),
    path('<uuid:pk>/read/', views.MarkMessageReadView.as_view(), name='mark-read'),
    path('unread-count/', views.UnreadMessageCountView.as_view(), name='unread-count'),
]
