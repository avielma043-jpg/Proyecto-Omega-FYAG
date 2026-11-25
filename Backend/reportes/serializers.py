"""
Serializadores explícitos para el Dashboard y Reportes (Solo lectura).
"""
from rest_framework import serializers
from obras.models import Obra
from logistica.models import Articulo


class RentabilidadObraSerializer(serializers.ModelSerializer):
    """Mapea los cálculos de rentabilidad generados por el ORM."""
    monto_presupuesto = serializers.IntegerField(read_only=True)
    costo_materiales = serializers.IntegerField(read_only=True)
    costo_horas = serializers.IntegerField(read_only=True)
    margen_neto = serializers.IntegerField(read_only=True)

    class Meta:
        model = Obra
        fields = [
            'id', 
            'tipo_servicio', 
            'estado', 
            'fecha_creacion',
            'monto_presupuesto', 
            'costo_materiales', 
            'costo_horas', 
            'margen_neto'
        ]


class AlertaStockSerializer(serializers.ModelSerializer):
    """Mapea los artículos críticos y su déficit calculado."""
    deficit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Articulo
        fields = [
            'id', 
            'codigo_interno', 
            'nombre', 
            'stock_disponible', 
            'stock_minimo', 
            'deficit'
        ]