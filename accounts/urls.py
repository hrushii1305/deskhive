from django.urls import path
from .views import (
    RegisterView, CustomerRegisterView, AgentJoinRequestView,
    PendingAgentListView, ApproveAgentView, RejectAgentView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('register/customer/', CustomerRegisterView.as_view(), name='register-customer'),
    path('register/agent/', AgentJoinRequestView.as_view(), name='register-agent'),
    path('pending-agents/', PendingAgentListView.as_view(), name='pending-agents'),
    path('pending-agents/<int:member_id>/approve/', ApproveAgentView.as_view(), name='approve-agent'),
    path('pending-agents/<int:member_id>/reject/', RejectAgentView.as_view(), name='reject-agent'),
]