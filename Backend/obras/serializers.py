"""
Serializadores explícitos para el módulo Obras.
"""
import re
from rest_framework import serializers
from .models import (
    ClienteMandante, ContactoCliente, Presupuesto,
    Obra, HojaServicio, HorasTrabajadas
)


def validar_rut_chileno(value: str) -> str:

    if not re.match(r'^\d{7,8}-[kK0-9]$', value):
    
        raise serializers.ValidationError("Formato de RUT inválido. Utilice el formato 12345678-9.")
    
    return value



class ContactoClienteSerializer(serializers.ModelSerializer):

    rut = serializers.CharField(max_length=12, validators=[validar_rut_chileno])

    class Meta:
        model = ContactoCliente
        fields = ['id', 'id_cliente', 'nombre', 'rut', 'cargo', 'email', 'telefono']


class ClienteMandanteSerializer(serializers.ModelSerializer):
    contactos = ContactoClienteSerializer(many=True, read_only=True)

    class Meta:
        model = ClienteMandante
        fields = ['id', 'rut', 'razon_social', 'giro', 'contactos']


class PresupuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Presupuesto
        fields = ['id', 'id_cliente', 'estado', 'monto_total']
        read_only_fields = ['id']


class HojaServicioSerializer(serializers.ModelSerializer):

    client_uuid = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = HojaServicio
        fields = ['id', 'client_uuid', 'id_obra', 'fecha_servicio', 'ruta_fotografia', 'firma_canvas_base64', 'estado_firma']
        read_only_fields = ['id', 'fecha_servicio']


class HorasTrabajadasSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorasTrabajadas
        fields = ['id', 'id_obra', 'id_tecnico', 'cantidad_horas', 'costo_hora']


class ObraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Obra
        fields = ['id', 'id_presupuesto', 'id_cliente', 'id_tecnico', 'tipo_servicio', 'estado', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion']