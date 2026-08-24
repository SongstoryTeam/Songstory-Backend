from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user == getattr(obj, "creator", None) or request.user.is_staff


class IsCreatorOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        creator = getattr(obj, "creator", None) or getattr(obj, "user", None)
        return request.user == creator or request.user.is_staff


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_staff