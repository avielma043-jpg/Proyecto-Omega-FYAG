"""
Serializadores explícitos para el módulo de Compras.
"""
import re
from decimal import Decimal
from rest_framework import serializers
from .models import Proveedor, ContactoProveedor, DocumentoCompra, DetalleCompra


def validar_rut_chileno(value: str) -> str:

    """Valida el formato básico del RUT (ej: 12345678-9 o 1234567-K)."""
    if not re.match(r'^\d{7,8}-[kK0-9]$', value):
    
        raise serializers.ValidationError("Formato de RUT inválido. Utilice el formato 12345678-9.")
    
    return value

class ContactoProveedorSerializer(serializers.ModelSerializer):

    rut = serializers.CharField(max_length=12, validators=[validar_rut_chileno])

    class Meta:
        model = ContactoProveedor
        fields = ['id', 'id_proveedor', 'nombre', 'rut', 'cargo', 'email', 'telefono']
    

class ProveedorSerializer(serializers.ModelSerializer):
    contactos = ContactoProveedorSerializer(many=True, read_only=True)

    class Meta:
        model = Proveedor
        fields = [
            'id', 'rut', 'razon_social', 'direccion', 'banco', 
            'tipo_cuenta', 'numero_cuenta', 'email_pagos', 'contactos'
        ]


class DetalleCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleCompra
        fields = [
            'id', 'id_articulo', 'cantidad', 'costo_base', 
            'descuento_1', 'descuento_2', 'descuento_3', 'costo_neto_final'
        ]
        read_only_fields = ['id', 'costo_neto_final'] # Se calcula por BD (save)


class DocumentoCompraSerializer(serializers.ModelSerializer):
    detalles = DetalleCompraSerializer(many=True)

    class Meta:
        model = DocumentoCompra
        fields = [
            'id', 'id_proveedor', 'tipo_documento', 'folio', 'fecha_ingreso',
            'subtotal', 'descuentos_generales', 'descuento_pago_anticipado',
            'total_neto', 'iva', 'total_final', 'detalles'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        
        subtotal = 0
        
        # 1. Procesar cada detalle y calcular la cascada de descuentos
        for detalle in detalles_data:
            costo_base = detalle.get('costo_base', 0)
            d1 = detalle.get('descuento_1', Decimal('0.0000'))
            d2 = detalle.get('descuento_2', Decimal('0.0000'))
            d3 = detalle.get('descuento_3', Decimal('0.0000'))
            cantidad = detalle.get('cantidad', Decimal('0.00'))
            
            # Fórmula de cascada (multiplicativa)
            factor = (Decimal('1') - d1) * (Decimal('1') - d2) * (Decimal('1') - d3)
            costo_neto_final = int(round(Decimal(costo_base) * factor))
            
            # Asignamos el valor calculado al dict del detalle
            detalle['costo_neto_final'] = costo_neto_final
            
            # 2. Sumar al subtotal del documento (costo neto * cantidad fraccionaria)
            subtotal += int(round(Decimal(costo_neto_final) * cantidad))

        descuentos_generales = validated_data.get('descuentos_generales', 0)
        descuento_pago = validated_data.get('descuento_pago_anticipado', 0)

        # 3. Calcular Total Neto (sin saldo negativo)
        total_neto = max(0, subtotal - descuentos_generales - descuento_pago)
        
        # 4. Calcular IVA (19%) y Total Final en enteros
        iva = int(round(total_neto * 0.19))
        total_final = total_neto + iva

        # Inyectar totales calculados al documento
        validated_data['subtotal'] = subtotal
        validated_data['total_neto'] = total_neto
        validated_data['iva'] = iva
        validated_data['total_final'] = total_final

        # Persistir Documento y sus Detalles
        documento = DocumentoCompra.objects.create(**validated_data)
        for detalle_data in detalles_data:
            DetalleCompra.objects.create(id_documento=documento, **detalle_data)
            
        return documento