from django.db import transaction, IntegrityError
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response

from .models import Articulo, Cardex
from .serializers import ArticuloSerializer, CardexSerializer
from core.permissions import CanReadArticulosOrWriteBodega, CanAccessCardex
from core.models import LogAuditoria, Rol

class ArticuloListCreateAPIView(generics.ListCreateAPIView):
    queryset = Articulo.objects.all().order_by('id')
    serializer_class = ArticuloSerializer
    permission_classes = [CanReadArticulosOrWriteBodega]

class ArticuloDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Articulo.objects.all()
    serializer_class = ArticuloSerializer
    permission_classes = [CanReadArticulosOrWriteBodega]

    def perform_update(self, serializer):
        usuario = self.request.user
        es_bodega = (not usuario.is_superuser and usuario.rol and usuario.rol.nombre_rol == Rol.BODEGA)
        
        # Regla de negocio: Bodega no puede alterar el precio_lista_vigente sin un documento de compra
        if es_bodega and 'precio_lista_vigente' in serializer.validated_data:
            nuevo_precio = serializer.validated_data['precio_lista_vigente']
            if nuevo_precio != self.get_object().precio_lista_vigente:
                raise PermissionDenied("Bodega no puede alterar el precio de lista manualmente sin documento de compra.")
        serializer.save()

class CardexListCreateAPIView(generics.ListCreateAPIView):
    queryset = Cardex.objects.select_related('id_articulo', 'id_usuario', 'id_obra').all()
    serializer_class = CardexSerializer
    permission_classes = [CanAccessCardex]

    @transaction.atomic
    def perform_create(self, serializer):
        data = serializer.validated_data
        tipo = data['tipo_movimiento']
        cantidad = data['cantidad']
        usuario = self.request.user
        rol_actual = usuario.rol.nombre_rol if usuario.rol else None
        
        # Validaciones de perfil vs tipo de movimiento
        if not usuario.is_superuser:
         if rol_actual == Rol.TECNICO:
             if tipo != Cardex.TIPO_EGRESO:
                 raise PermissionDenied("El perfil Técnico solo puede registrar egresos de material en obra.")
             obra = data.get('id_obra')
             if obra and obra.id_tecnico_id != usuario.id_usuario:
                 raise PermissionDenied("No puede imputar materiales a una obra asignada a otro técnico.")

         if tipo == Cardex.TIPO_REVERSA and rol_actual != Rol.ADMIN_GENERAL:
             raise PermissionDenied("Solo el Administrador General puede ejecutar movimientos de Reversa.")

        try:
            articulo = Articulo.objects.select_for_update().get(id=data['id_articulo'].id)
        except Articulo.DoesNotExist:
            raise ValidationError({"id_articulo": "El artículo no existe."})

        if tipo in [Cardex.TIPO_EGRESO, Cardex.TIPO_MERMA]:
            if articulo.stock_disponible < cantidad:
                raise ValidationError({"cantidad": f"Stock insuficiente. Disponible: {articulo.stock_disponible}"})
            articulo.stock_disponible -= cantidad
        elif tipo in [Cardex.TIPO_INGRESO, Cardex.TIPO_DEVOLUCION]:
            articulo.stock_disponible += cantidad
        elif tipo == Cardex.TIPO_REVERSA:
            mov_original = data['id_movimiento_original']
            if mov_original.tipo_movimiento in [Cardex.TIPO_EGRESO, Cardex.TIPO_MERMA]:
                articulo.stock_disponible += cantidad
            else:
                if articulo.stock_disponible < cantidad:
                    raise ValidationError({"cantidad": "Stock insuficiente para reversar este ingreso."})
                articulo.stock_disponible -= cantidad
        
        articulo.save()
        
        # Valorizar egresos al último precio de lista
        precio_aplicado = articulo.precio_lista_vigente if tipo == Cardex.TIPO_EGRESO else data['precio_unitario']
        movimiento = serializer.save(id_usuario=usuario, precio_unitario=precio_aplicado)
        
        LogAuditoria.objects.create(
            usuario=usuario,
            tabla_afectada='logistica_cardex',
            tipo_operacion=LogAuditoria.OP_INSERT,
            valor_anterior=None,
            valor_nuevo={
                'id_movimiento': movimiento.id,
                'id_articulo': articulo.id,
                'id_obra': movimiento.id_obra_id,
                'tipo_movimiento': tipo,
                'cantidad': float(cantidad),
                'stock_resultante': float(articulo.stock_disponible)
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_uuid = serializer.validated_data.get('client_uuid')
        if client_uuid:
            existente = Cardex.objects.select_related(
                'id_articulo', 'id_usuario', 'id_obra'
            ).filter(client_uuid=client_uuid).first()
            if existente:
                output = self.get_serializer(existente)
                return Response(output.data, status=status.HTTP_200_OK)

        try:
            self.perform_create(serializer)
        except IntegrityError:
            # Respaldo ante dos reintentos simultáneos en el mismo milisegundo
            if client_uuid:
                existente = Cardex.objects.get(client_uuid=client_uuid)
                return Response(self.get_serializer(existente).data, status=status.HTTP_200_OK)
            raise

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)