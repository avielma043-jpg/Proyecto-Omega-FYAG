"""
Permisos específicos para el módulo de Compras.
"""
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import View

from core.models import Rol
from core.permissions import _tiene_rol


class CanAccessCompras(BasePermission):
    """
    Limita el acceso al módulo de compras a los roles autorizados.
    """
    message = "No tiene permisos para acceder a compras. Requiere perfil Administración, Administrador General o Bodega."

    def has_permission(self, request: Request, view: View) -> bool:
        return _tiene_rol(request, [
            Rol.ADMIN_GENERAL,
            Rol.ADMINISTRACION,
            Rol.BODEGA
        ])