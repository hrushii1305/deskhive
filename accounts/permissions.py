from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Allows access only to authenticated users who are owners of an org."""
    def has_permission(self, request, view):
        member = getattr(request.user, 'member', None)
        return member is not None and member.role == 'owner'
    
    
class IsApprovedMember(BasePermission):
    """
    Allows access only to members whose status is 'approved'.
    Blocks pending/rejected agents from accessing app data until an owner
    approves them. (Owners and customers are 'approved' by default.)
    """
    message = "Your account is pending approval."

    def has_permission(self, request, view):
        member = getattr(request.user, 'member', None)
        return member is not None and member.status == 'approved'