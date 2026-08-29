from django.urls import path
from .views import RegisterView, CustomerRegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('register/customer/', CustomerRegisterView.as_view(), name='register-customer'),
]