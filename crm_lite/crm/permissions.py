from rest_framework import permissions


class IsCompanyOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_company_owner

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'company'):
            return obj.company == request.user.company
        elif hasattr(obj, 'user_set'):
            return obj == request.user.company
        return False


class IsCompanyEmployee(permissions.BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                hasattr(request.user, 'company') and
                request.user.company is not None)

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'company'):
            return obj.company == request.user.company
        elif hasattr(obj, 'supplier'):
            return obj.supplier.company == request.user.company
        elif hasattr(obj, 'storage'):
            return obj.storage.company == request.user.company
        return False