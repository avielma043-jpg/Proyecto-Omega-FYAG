from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import LogAuditoria, Usuario
from .permissions import IsAdminOAdministracion
from .serializers import CustomTokenObtainPairSerializer, UsuarioSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
	"""Endpoint de Login que retorna los tokens y claims de rol."""
	serializer_class = CustomTokenObtainPairSerializer


class UsuarioListCreateAPIView(generics.ListCreateAPIView):
	"""
	GET: Lista todos los usuarios.
	POST: Crea un nuevo usuario y le asigna un rol RBAC, registrando auditoría.
	"""
	queryset = Usuario.objects.select_related('rol').all().order_by('id_usuario')
	serializer_class = UsuarioSerializer
	permission_classes = [IsAdminOAdministracion]

	def perform_create(self, serializer):
		usuario_creado = serializer.save()
		LogAuditoria.objects.create(
			usuario=self.request.user,
			tabla_afectada='usuarios',
			tipo_operacion=LogAuditoria.OP_INSERT,
			valor_anterior=None,
			valor_nuevo={
				'id_usuario': usuario_creado.id_usuario,
				'username': usuario_creado.username,
				'rut': usuario_creado.rut,
				'rol': usuario_creado.rol.nombre_rol if usuario_creado.rol else None,
				'estado_activo': usuario_creado.estado_activo,
			}
		)


class UsuarioDetailAPIView(generics.RetrieveUpdateAPIView):
	"""
	GET: Consulta el detalle de un usuario.
	PATCH/PUT: Permite reasignar rol o cambiar estado_activo con trazabilidad.
	"""
	queryset = Usuario.objects.select_related('rol').all()
	serializer_class = UsuarioSerializer
	permission_classes = [IsAdminOAdministracion]
	lookup_field = 'id_usuario'

	def perform_update(self, serializer):
		instancia_previa = self.get_object()
		snapshot_anterior = {
			'rol': instancia_previa.rol.nombre_rol if instancia_previa.rol else None,
			'estado_activo': instancia_previa.estado_activo,
		}
		usuario_actualizado = serializer.save()
		LogAuditoria.objects.create(
			usuario=self.request.user,
			tabla_afectada='usuarios',
			tipo_operacion=LogAuditoria.OP_UPDATE,
			valor_anterior=snapshot_anterior,
			valor_nuevo={
				'rol': usuario_actualizado.rol.nombre_rol if usuario_actualizado.rol else None,
				'estado_activo': usuario_actualizado.estado_activo,
			}
		)