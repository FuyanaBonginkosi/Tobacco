from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile Management
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/end-session/', views.end_session, name='end_session'),
    
    # QR Code Features
    path('qr/generate/', views.generate_secure_qr, name='generate_secure_qr'),
    path('qr/verify/<str:token>/', views.verify_qr_token, name='verify_qr_token'),
]