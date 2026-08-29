from django.urls import path
from .views import OrganizationListView

urlpatterns = [
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
]