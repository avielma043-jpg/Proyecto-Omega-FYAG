"""
Serializadores explícitos para el módulo de Logística y Cardex.
"""
from rest_framework import serializers

from .models import Articulo, Cardex


class ArticuloSerializer(serializers.ModelSerializer):
    """Serializador explícito para el catálogo de artículos."""

    class Meta:
        model = Articulo
        fields = [
            'id',
            'codigo_interno',
            'codigo_barras',
            'nombre',
            'categoria',
            'unidad_medida',
            'ubicacion',
            'stock_disponible',
            'stock_comprometido',
            'stock_minimo',
            'ultimo_costo',
            'precio_lista_vigente',
        ]
        read_only_fields = [
            'id',
            'stock_disponible',
            'stock_comprometido',
            'ultimo_costo',
        ]


class CardexSerializer(serializers.ModelSerializer):
    """Serializador explícito para los movimientos inmutables del Cardex."""
    articulo_nombre = serializers.CharField(source='id_articulo.nombre', read_only=True)
    usuario_username = serializers.CharField(source='id_usuario.username', read_only=True)
    client_uuid = serializers.UUIDField(required=False, allow_null=True)
    class Meta:
        model = Cardex
        fields = [
            'id',
            'id_articulo',
            'client_uuid',
            'articulo_nombre',
            'id_usuario',
            'usuario_username',
            'id_obra',
            'tipo_movimiento',
            'cantidad',
            'precio_unitario',
            'fecha_movimiento',
            'motivo_reversa',
            'id_movimiento_original',
        ]
        read_only_fields = [
            'id',
            'articulo_nombre',
            'id_usuario',
            'usuario_username',
            'fecha_movimiento',
        ]

    def validate(self, data: dict) -> dict:
        tipo = data.get('tipo_movimiento')

        # 1. Validación de Egresos
        if tipo == Cardex.TIPO_EGRESO and not data.get('id_obra'):
            raise serializers.ValidationError(
                {"id_obra": "El ID de la obra es obligatorio para registrar un Egreso."}
            )

        # 2. Validación de Reversas
        if tipo == Cardex.TIPO_REVERSA:
            if not data.get('id_movimiento_original'):
                raise serializers.ValidationError(
                    {"id_movimiento_original": "Debe indicar el movimiento original a reversar."}
                )
            if not data.get('motivo_reversa') or len(data.get('motivo_reversa').strip()) < 5:
                raise serializers.ValidationError(
                    {"motivo_reversa": "Debe proveer una justificación detallada para la reversa."}
                )

        return data