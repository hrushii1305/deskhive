from .serializers import RegisterSerializer, CustomerRegisterSerializer, AgentJoinRequestSerializer, PendingAgentSerializer, MeSerializer  # update this import
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .tasks import send_agent_request_email, send_agent_decision_email
from .permissions import IsOwner
from .models import Member
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView


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
        
class AgentJoinRequestView(generics.CreateAPIView):
    """
    POST /api/register/agent/

    Public endpoint: an agent REQUESTS to join an existing organization.
    Creates a PENDING member (role=agent, status=pending) and notifies the
    org owner. The agent cannot access anything until the owner approves.
    """
    serializer_class = AgentJoinRequestSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()

        # notify the org owner (async, via Celery)
        try:
            send_agent_request_email.delay(member.id)
        except Exception:
                pass  # email notification is best-effort; don't fail the request if the broker is down
        
        return Response(
            {
                "detail": "Join request submitted. Awaiting owner approval.",
                "username": member.user.username,
                "organization": member.organization.name,
                "role": member.role,
                "status": member.status,
            },
            status=status.HTTP_201_CREATED,
        )
        


class PendingAgentListView(generics.ListAPIView):
    """
    GET /api/pending-agents/

    Owner-only. Lists agents with pending requests IN THE OWNER'S OWN ORG.
    """
    serializer_class = PendingAgentSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        owner = self.request.user.member
        # scoped to the owner's org + only pending agents
        return Member.objects.filter(
            organization=owner.organization,
            role='agent',
            status='pending',
        )


class ApproveAgentView(APIView):
    """
    POST /api/pending-agents/<id>/approve/

    Owner-only. Approves a pending agent — but only if that agent
    is in the approving owner's OWN organization.
    """
    permission_classes = [IsAuthenticated, IsOwner]

    def post(self, request, member_id):
        owner = request.user.member
        try:
            # the org filter is the tenant-isolation guard:
            # an owner can only touch pending agents in THEIR org.
            agent = Member.objects.get(
                id=member_id,
                organization=owner.organization,
                role='agent',
                status='pending',
            )
        except Member.DoesNotExist:
            raise NotFound("Pending agent not found in your organization.")

        agent.status = 'approved'
        agent.save()

        # notify the agent they were approved (async)
        send_agent_decision_email.delay(agent.id, 'approved')

        return Response(
            {"detail": f"{agent.name} approved.", "status": agent.status},
            status=status.HTTP_200_OK,
        )


class RejectAgentView(APIView):
    """
    POST /api/pending-agents/<id>/reject/

    Owner-only. Rejects a pending agent in the owner's OWN organization.
    """
    permission_classes = [IsAuthenticated, IsOwner]

    def post(self, request, member_id):
        owner = request.user.member
        try:
            agent = Member.objects.get(
                id=member_id,
                organization=owner.organization,
                role='agent',
                status='pending',
            )
        except Member.DoesNotExist:
            raise NotFound("Pending agent not found in your organization.")

        agent.status = 'rejected'
        agent.save()

        send_agent_decision_email.delay(agent.id, 'rejected')

        return Response(
            {"detail": f"{agent.name} rejected.", "status": agent.status},
            status=status.HTTP_200_OK,
        )
        
        

class MeView(generics.RetrieveAPIView):
    """
    GET /api/me/

    Returns the currently authenticated user's member info (role, status, etc.)
    so the frontend can render role-aware UI.
    """
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.member