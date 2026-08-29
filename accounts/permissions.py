from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Allows access only to authenticated users who are owners of an org."""
    def has_permission(self, request, view):
        member = getattr(request.user, 'member', None)
        return member is not None and member.role == 'owner'