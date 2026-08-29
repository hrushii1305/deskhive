from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationListView(generics.ListAPIView):
    """
    GET /api/organizations/

    Public endpoint listing active organizations, so a signup form can
    show which org a new customer/agent wants to join.
    """
    queryset = Organization.objects.filter(is_active=True)
    serializer_class = OrganizationSerializer
    permission_classes = [AllowAny]