from rest_framework import permissions


class IsCompanyOwner(permissions.BasePermission):
    """
    Разрешение только для владельцев компании
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_company_owner

    def has_object_permission(self, request, view, obj):
        # Для объектов, связанных с компанией через поле company
        if hasattr(obj, 'company'):
            return obj.company == request.user.company
        # Для самой компании
        elif hasattr(obj, 'user_set'):
            return obj == request.user.company
        return False


class IsCompanyEmployee(permissions.BasePermission):
    """
    Разрешение для сотрудников компании (включая владельца)
    """

    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                hasattr(request.user, 'company') and
                request.user.company is not None)

    def has_object_permission(self, request, view, obj):
        # Для объектов, связанных с компанией
        if hasattr(obj, 'company'):
            return obj.company == request.user.company
        # Для поставщиков
        elif hasattr(obj, 'supplier__company'):
            return obj.supplier.company == request.user.company
        return False