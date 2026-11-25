from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import View

from .models import Rol

def _tiene_rol(request: Request, roles_permitidos: list[str]) -> bool:
    """Función auxiliar que verifica autenticación, actividad y pertenencia al rol."""
    user = request.user
    if not (user and user.is_authenticated and user.estado_activo):
        return False
    if user.is_superuser:
        return True
    return bool(user.rol and user.rol.nombre_rol in roles_permitidos)

class IsAdministradorGeneral(BasePermission):
    message = "No tiene permisos para realizar esta acción. Se requiere perfil Administrador General."
    def has_permission(self, request: Request, view: View) -> bool:
        return _tiene_rol(request, [Rol.ADMIN_GENERAL])

class IsAdminOAdministracion(BasePermission):
    message = "No tiene permisos para gestionar usuarios. Se requiere perfil Administrador General o Administración."
    def has_permission(self, request: Request, view: View) -> bool:
        return _tiene_rol(request, [Rol.ADMIN_GENERAL, Rol.ADMINISTRACION])

class CanReadArticulosOrWriteBodega(BasePermission):
    """
    GET: Todos los perfiles pueden consultar el catálogo (necesario para cotizar o despachar).
    POST/PUT/PATCH: Solo Bodega, Administración y Administrador General.
    """
    message = "No tiene permisos para modificar el catálogo de artículos."
    def has_permission(self, request: Request, view: View) -> bool:
        if request.method in SAFE_METHODS:
            return _tiene_rol(request, [
                Rol.ADMIN_GENERAL, Rol.ADMINISTRACION, Rol.BODEGA, 
                Rol.SUPERVISOR, Rol.TECNICO, Rol.CONSULTA
            ])
        return _tiene_rol(request, [Rol.ADMIN_GENERAL, Rol.ADMINISTRACION, Rol.BODEGA])

class CanAccessCardex(BasePermission):
    """
    GET: Administración, General, Bodega, Supervisor y Consulta pueden auditar el inventario.
    POST: Bodega, Administrador General y Técnico (restringido a egresos en la vista).
    """
    message = "No tiene permisos para operar sobre el Cardex."
    def has_permission(self, request: Request, view: View) -> bool:
        if request.method in SAFE_METHODS:
            return _tiene_rol(request, [
                Rol.ADMIN_GENERAL, Rol.ADMINISTRACION, Rol.BODEGA, 
                Rol.SUPERVISOR, Rol.CONSULTA
            ])
        if request.method == 'POST':
            return _tiene_rol(request, [Rol.ADMIN_GENERAL, Rol.BODEGA, Rol.TECNICO])
        return False