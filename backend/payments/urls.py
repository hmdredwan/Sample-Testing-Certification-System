from django.urls import path
from . import views

urlpatterns = [
    # User payments
    path('', views.UserPaymentListView.as_view(), name='user-payments'),
    path('create/', views.CreatePaymentView.as_view(), name='create-payment'),
    path('<uuid:pk>/', views.UserPaymentDetailView.as_view(), name='user-payment-detail'),

    # Admin payments
    path('admin/', views.AdminPaymentListView.as_view(), name='admin-payments'),
    path('admin/<uuid:pk>/', views.AdminPaymentDetailView.as_view(), name='admin-payment-detail'),
]
