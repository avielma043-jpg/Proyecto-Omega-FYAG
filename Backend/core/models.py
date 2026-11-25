from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import JSONField


"""
Modelos de datos para el módulo de Seguridad, Roles (RBAC) y Auditoría.
Cumple con las especificaciones del Proyecto Omega (FYAG).
"""
class Rol(models.Model):
	"""
	Tabla paramétrica para el Control de Acceso Basado en Roles (RBAC).
	Limitada estrictamente a los 6 perfiles de negocio de FYAG.
	"""
	ADMIN_GENERAL = 'Administrador General'
	ADMINISTRACION = 'Administración'
	BODEGA = 'Bodega/Logística'
	SUPERVISOR = 'Supervisor de Obras'
	TECNICO = 'Técnico'
	CONSULTA = 'Consulta'

	ROLES_CHOICES = [
		(ADMIN_GENERAL, 'Administrador General'),
		(ADMINISTRACION, 'Administración'),
		(BODEGA, 'Bodega/Logística'),
		(SUPERVISOR, 'Supervisor de Obras'),
		(TECNICO, 'Técnico'),
		(CONSULTA, 'Consulta'),
	]

	id_rol = models.AutoField(primary_key=True)
	nombre_rol = models.CharField(
		max_length=50,
		choices=ROLES_CHOICES,
		unique=True
	)

	class Meta:
		db_table = 'roles'
		verbose_name = 'Rol'
		verbose_name_plural = 'Roles'

	def __str__(self) -> str:
		return self.nombre_rol


class Usuario(AbstractUser):
	"""
	Modelo de usuario personalizado para FYAG.
	Extiende AbstractUser incorporando RUT único y vínculo directo al Rol RBAC.
	"""
	id_usuario = models.AutoField(primary_key = True)
	rut = models.CharField(max_length = 12, unique = True)
	rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name='usuarios', db_column='id_rol', null=True, blank=True)
	estado_activo = models.BooleanField(default=True)

	# Desacoplamiento de tablas M2M por defecto si se gestiona 100% vía Rol
	groups = None
	user_permissions = None

	class Meta:

		db_table = 'usuarios'
		verbose_name = 'Usuario'
		verbose_name_plural = 'Usuarios'

	def save(self, *args, **kwargs):

		# Sincroniza estado_activo con is_active nativo de Django (usado por SimpleJWT)
		self.is_active = self.estado_activo
		super().save(*args, **kwargs)

	def __str__(self) -> str:

		rol_nombre = self.rol.nombre_rol if self.rol else 'Sin Rol'
		return f"{self.username} ({self.rut}) - {rol_nombre}"


class LogAuditoria(models.Model):
	"""
	Bitácora inmutable (Append-Only) para trazabilidad de operaciones críticas.
	Almacena snapshots en formato JSON nativo de PostgreSQL.
	"""
	OP_INSERT = 'INSERT'
	OP_UPDATE = 'UPDATE'
	OP_REVERSA = 'REVERSA'

	OPERACION_CHOICES = [

		(OP_INSERT, 'Inserción'),
		(OP_UPDATE, 'Actualización'),
		(OP_REVERSA, 'Reversa / Anulación'),
	
	]

	id_log = models.AutoField(primary_key=True)

	usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='logs_auditoria', db_column='id_usuario')
	tabla_afectada = models.CharField(max_length=100)
	fecha_hora = models.DateTimeField(auto_now_add=True)
	tipo_operacion = models.CharField(max_length=20, choices=OPERACION_CHOICES)
	valor_anterior = JSONField(null=True, blank=True)
	valor_nuevo = JSONField(null=True, blank=True)

	class Meta:

		db_table = 'log_auditoria'
		ordering = ['-fecha_hora']
		verbose_name = 'Log de Auditoría'
		verbose_name_plural = 'Logs de Auditoría'

	def __str__(self) -> str:

		return f"[{self.fecha_hora}] {self.tipo_operacion} en {self.tabla_afectada} por ID:{self.usuario_id}"