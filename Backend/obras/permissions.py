"""
Permisos granulares para el módulo de Obras y Terreno.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import View

from core.models import Rol
from core.permissions import _tiene_rol


class CanAccessFinanzasObra(BasePermission):
    """
    Bloquea completamente al Técnico.
    Solo permite acceso a Administrador, Administración y Supervisor.
    """
    message = "No tiene permisos. Requiere perfil Administrador General, Administración o Supervisor."

    def has_permission(self, request: Request, view: View) -> bool:
        return _tiene_rol(request, [
            Rol.ADMIN_GENERAL,
            Rol.ADMINISTRACION,
            Rol.SUPERVISOR
        ])


class CanManageObras(BasePermission):
    """
    Lectura (GET): Admin, Admin, Supervisor y Técnico.
    Escritura (POST, PUT, PATCH): Admin, Admin, Supervisor.
    """
    message = "No tiene permisos para modificar o gestionar obras."

    def has_permission(self, request: Request, view: View) -> bool:
        if request.method in SAFE_METHODS:
            return _tiene_rol(request, [
                Rol.ADMIN_GENERAL,
                Rol.ADMINISTRACION,
                Rol.SUPERVISOR,
                Rol.TECNICO
            ])
        return _tiene_rol(request, [
            Rol.ADMIN_GENERAL,
            Rol.ADMINISTRACION,
            Rol.SUPERVISOR
        ])


class CanManageTerreno(BasePermission):
    """
    Permite a los Técnicos registrar Hojas de Servicio y Horas Trabajadas en terreno.
    """
    message = "No tiene permisos para gestionar operaciones en terreno."

    def has_permission(self, request: Request, view: View) -> bool:
        return _tiene_rol(request, [
            Rol.ADMIN_GENERAL,
            Rol.ADMINISTRACION,
            Rol.SUPERVISOR,
            Rol.TECNICO
        ])