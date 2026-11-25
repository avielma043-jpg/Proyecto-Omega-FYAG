"""
Modelos de datos para el módulo de Compras y Proveedores (Proyecto Omega - FYAG).
"""
from django.db import models
from logistica.models import Articulo


class Proveedor(models.Model):
    id = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True)
    razon_social = models.CharField(max_length=200)
    direccion = models.CharField(max_length=250)
    banco = models.CharField(max_length=100, blank=True, null=True)
    tipo_cuenta = models.CharField(max_length=50, blank=True, null=True)
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True)
    email_pagos = models.EmailField(blank=True, null=True)

    class Meta:
        db_table = 'compras_proveedor'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return f"{self.razon_social} ({self.rut})"


class ContactoProveedor(models.Model):
    id = models.AutoField(primary_key=True)
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='contactos')
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12)
    cargo = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)

    class Meta:
        db_table = 'compras_contacto_proveedor'


class DocumentoCompra(models.Model):
    TIPO_FACTURA = 'Factura'
    TIPO_BOLETA = 'Boleta'
    TIPO_GUIA = 'Guía'
    TIPO_NOTA_CREDITO = 'Nota de Crédito'

    DOCUMENTO_CHOICES = [
        (TIPO_FACTURA, 'Factura'),
        (TIPO_BOLETA, 'Boleta'),
        (TIPO_GUIA, 'Guía de Despacho'),
        (TIPO_NOTA_CREDITO, 'Nota de Crédito'),
    ]

    id = models.AutoField(primary_key=True)
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='documentos')
    tipo_documento = models.CharField(max_length=30, choices=DOCUMENTO_CHOICES)
    folio = models.CharField(max_length=50)
    fecha_ingreso = models.DateField()

    # Campos financieros obligatoriamente en Integer (Pesos Chilenos)
    subtotal = models.IntegerField(default=0)
    descuentos_generales = models.IntegerField(default=0)
    descuento_pago_anticipado = models.IntegerField(default=0)
    total_neto = models.IntegerField(default=0)
    iva = models.IntegerField(default=0)
    total_final = models.IntegerField(default=0)

    class Meta:
        db_table = 'compras_documento'


class DetalleCompra(models.Model):
    id = models.AutoField(primary_key=True)
    id_documento = models.ForeignKey(DocumentoCompra, on_delete=models.CASCADE, related_name='detalles')
    id_articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT)
    
    # Cantidad fraccionaria
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Costos en enteros
    costo_base = models.IntegerField()
    costo_neto_final = models.IntegerField(blank=True) # Calculado automáticamente
    
    # Descuentos sucesivos (Ej: 0.1000 para 10%)
    descuento_1 = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    descuento_2 = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    descuento_3 = models.DecimalField(max_digits=5, decimal_places=4, default=0)

    class Meta:
        db_table = 'compras_detalle'

    def save(self, *args, **kwargs):
        """Regla de Negocio 1: Fórmula de cascada (multiplicativa, sin suma lineal)"""
        from decimal import Decimal
        d1 = self.descuento_1 or Decimal('0.0000')
        d2 = self.descuento_2 or Decimal('0.0000')
        d3 = self.descuento_3 or Decimal('0.0000')
        
        factor = (Decimal('1') - d1) * (Decimal('1') - d2) * (Decimal('1') - d3)
        self.costo_neto_final = int(round(Decimal(self.costo_base) * factor))
        
        super().save(*args, **kwargs)