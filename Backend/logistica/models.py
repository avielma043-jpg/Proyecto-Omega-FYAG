"""
Modelos de datos para el módulo de Logística y Bodega (Proyecto Omega - FYAG).
"""
from django.db import models
from django.conf import settings

class Articulo(models.Model):
    """
    Catálogo de artículos, insumos y repuestos de la bodega central.
    """
    id = models.AutoField(primary_key=True)
    codigo_interno = models.CharField(max_length=50, unique=True)
    codigo_barras = models.CharField(max_length=100, blank=True, null=True)
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=100)
    unidad_medida = models.CharField(max_length=20)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    
    # Cantidades fraccionarias (Decimal)
    stock_disponible = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_comprometido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Valores monetarios SIEMPRE en enteros (CLP)
    ultimo_costo = models.IntegerField(default=0)
    precio_lista_vigente = models.IntegerField(default=0)

    class Meta:
        db_table = 'logistica_articulos'
        verbose_name = 'Artículo'
        verbose_name_plural = 'Artículos'

    def __str__(self):
        return f"{self.codigo_interno} - {self.nombre}"


class Cardex(models.Model):
    """
    Registro inmutable (Append-Only) de todos los movimientos de inventario.
    """
    TIPO_INGRESO = 'Ingreso'
    TIPO_EGRESO = 'Egreso'
    TIPO_MERMA = 'Merma'
    TIPO_CAMBIO = 'Cambio'
    TIPO_DEVOLUCION = 'Devolucion'
    TIPO_REVERSA = 'Reversa'

    MOVIMIENTO_CHOICES = [
        (TIPO_INGRESO, 'Ingreso'),
        (TIPO_EGRESO, 'Egreso'),
        (TIPO_MERMA, 'Merma'),
        (TIPO_CAMBIO, 'Cambio'),
        (TIPO_DEVOLUCION, 'Devolucion'),
        (TIPO_REVERSA, 'Reversa'),
    ]

    id = models.AutoField(primary_key=True)
    id_articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT, related_name='movimientos_cardex')
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='movimientos_bodega')
    
    client_uuid = models.UUIDField(unique=True, null=True, blank=True, db_index=True, help_text="UUID v4 generado en dispositivo para idempotencia offline")
    
    id_obra = models.ForeignKey('obras.Obra', on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos_cardex', help_text="Obra asociada (Obligatorio para Egresos)")
    
    tipo_movimiento = models.CharField(max_length=20, choices=MOVIMIENTO_CHOICES)
    
    # Cantidad fraccionaria y Precio en entero
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.IntegerField(help_text="Valorización del movimiento en CLP")
    
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    
    # Reversas
    motivo_reversa = models.TextField(blank=True, null=True, help_text="Justificación detallada (Solo para Reversas)")
    id_movimiento_original = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='reversas')

    class Meta:
        db_table = 'logistica_cardex'
        verbose_name = 'Movimiento Cardex'
        verbose_name_plural = 'Movimientos Cardex'
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.cantidad} {self.id_articulo.unidad_medida} ({self.fecha_movimiento})"