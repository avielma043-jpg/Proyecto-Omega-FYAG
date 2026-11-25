"""
Permisos analíticos y gerenciales para el módulo de Reportes.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import View

from core.models import Rol
from core.permissions import _tiene_rol


class CanViewDashboard(BasePermission):
    """
    Permite acceso de lectura (GET) a perfiles administrativos y operativos clave.
    Bloquea totalmente al perfil 'Técnico'.
    """
    message = "Acceso denegado. El perfil Técnico no tiene autorización para visualizar reportes gerenciales."

    def has_permission(self, request: Request, view: View) -> bool:
        if request.method in SAFE_METHODS:
            return _tiene_rol(request, [
                Rol.ADMIN_GENERAL,
                Rol.ADMINISTRACION,
                Rol.BODEGA,
                Rol.SUPERVISOR,
                Rol.CONSULTA
            ])
        return False