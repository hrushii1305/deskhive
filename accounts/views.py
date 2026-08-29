from .serializers import RegisterSerializer, CustomerRegisterSerializer  # update this import
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(
            {
                "message": "Registration successful",
                "member_id": member.id,
                "organization": member.organization.name,
                "role": member.role,
            },
            status=status.HTTP_201_CREATED,
        )
        

class CustomerRegisterView(generics.CreateAPIView):
    """
    POST /api/register/customer/

    Public endpoint: registers a new CUSTOMER into an existing organization.
    The role is forced to 'customer' server-side — never taken from the client.
    """
    serializer_class = CustomerRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(
            {
                "detail": "Customer account created.",
                "username": member.user.username,
                "organization": member.organization.name,
                "role": member.role,
            },
            status=status.HTTP_201_CREATED,
        )