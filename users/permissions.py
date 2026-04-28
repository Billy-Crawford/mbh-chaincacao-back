from rest_framework.permissions import BasePermission


class EstAgriculteur(BasePermission):
    message = "Seul un agriculteur peut effectuer cette action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'agriculteur'


class EstCooperative(BasePermission):
    message = "Seule une coopérative peut effectuer cette action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'cooperative'


class EstTransformateur(BasePermission):
    message = "Seul un transformateur peut effectuer cette action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'transformateur'


class EstExportateur(BasePermission):
    message = "Seul un exportateur peut effectuer cette action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'exportateur'


class EstActeurValide(BasePermission):
    """Tout utilisateur connecté avec un rôle valide."""
    message = "Vous devez avoir un rôle valide."
    ROLES_VALIDES = ['agriculteur', 'cooperative', 'transformateur', 'exportateur', 'verificateur']

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in self.ROLES_VALIDES