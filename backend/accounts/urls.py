from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('signin/', views.SigninView.as_view(), name='signin'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('signout/', views.SignoutView.as_view(), name='signout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Admin user management
    path('admin/users/', views.AllUsersListView.as_view(), name='admin-users'),
    path('admin/users/<uuid:pk>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/create-officer/', views.AdminCreateOfficerView.as_view(), name='admin-create-officer'),
    path('admin/users/create/', views.AdminCreateUserView.as_view(), name='admin-create-user'),
    path('admin/pending-officers/', views.PendingOfficersView.as_view(), name='pending-officers'),
    path('admin/approve-officer/<uuid:user_id>/', views.ApproveOfficerView.as_view(), name='approve-officer'),
    path('admin/reject-officer/<uuid:user_id>/', views.RejectOfficerView.as_view(), name='reject-officer'),
    path('admin/delete-user/<uuid:user_id>/', views.DeleteUserView.as_view(), name='delete-user'),
    path('admin/logs/', views.ActivityLogListView.as_view(), name='activity-logs'),
]
