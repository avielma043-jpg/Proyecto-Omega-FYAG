"""
Modelos de datos para el módulo de Clientes, Obras y Terreno (Proyecto Omega).
"""
from django.db import models
from django.conf import settings


class ClienteMandante(models.Model):
    id = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True)
    razon_social = models.CharField(max_length=200)
    giro = models.CharField(max_length=150)

    class Meta:
        db_table = 'obras_cliente_mandante'


class ContactoCliente(models.Model):
    id = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(ClienteMandante, on_delete=models.CASCADE, related_name='contactos')
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12)
    cargo = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)

    class Meta:
        db_table = 'obras_contacto_cliente'


class Presupuesto(models.Model):
    ESTADO_PENDIENTE = 'Pendiente'
    ESTADO_APROBADO = 'Aprobado'
    ESTADO_RECHAZADO = 'Rechazado'

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADO, 'Aprobado'),
        (ESTADO_RECHAZADO, 'Rechazado'),
    ]

    id = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(ClienteMandante, on_delete=models.PROTECT, related_name='presupuestos')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    
    # Restricción: Financiero siempre en Integer
    monto_total = models.IntegerField(default=0)

    class Meta:
        db_table = 'obras_presupuesto'


class Obra(models.Model):
    ESTADO_PROCESO = 'En proceso'
    ESTADO_FINALIZADA = 'Finalizada'
    ESTADO_SUSPENDIDA = 'Suspendida'
    ESTADO_CANCELADA = 'Cancelada'

    ESTADO_CHOICES = [
        (ESTADO_PROCESO, 'En proceso'),
        (ESTADO_FINALIZADA, 'Finalizada'),
        (ESTADO_SUSPENDIDA, 'Suspendida'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    id = models.AutoField(primary_key=True)
    id_presupuesto = models.ForeignKey(Presupuesto, on_delete=models.PROTECT, null=True, blank=True)
    id_cliente = models.ForeignKey(ClienteMandante, on_delete=models.PROTECT, related_name='obras')
    id_tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    client_uuid = models.UUIDField(unique=True, null=True, blank=True, db_index=True, help_text="UUID v4 generado en dispositivo para idempotencia offline")

    tipo_servicio = models.CharField(max_length=100)
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default=ESTADO_PROCESO)
    fecha_creacion = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'obras_obra'


class HojaServicio(models.Model):
    id = models.AutoField(primary_key=True)
    client_uuid = models.UUIDField(unique=True, null=True, blank=True, db_index=True, help_text="UUID v4 generado en dispositivo para idempotencia offline")

    id_obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name='hojas_servicio')
    fecha_servicio = models.DateTimeField(auto_now_add=True)
    
    # Restricciones: URL para fotos en cloud y TextField para firmas muy largas en Base64
    ruta_fotografia = models.URLField(max_length=500, blank=True, null=True)
    firma_canvas_base64 = models.TextField(blank=True, null=True)
    estado_firma = models.BooleanField(default=False)

    class Meta:
        db_table = 'obras_hoja_servicio'


class HorasTrabajadas(models.Model):
    id = models.AutoField(primary_key=True)
    id_obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name='horas_trabajadas')
    id_tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    # Restricciones: Horas en decimal (ej. 2.5 horas), costo monetario en enteros
    cantidad_horas = models.DecimalField(max_digits=5, decimal_places=2)
    costo_hora = models.IntegerField()

    class Meta:
        db_table = 'obras_horas_trabajadas'